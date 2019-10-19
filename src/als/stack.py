"""
Provides image stacking features
"""
# ALS - Astro Live Stacker
# Copyright (C) 2019  Sébastien Durand (Dragonlost) - Gilles Le Maréchal (Gehelem)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging
from multiprocessing import Process, Manager

import astroalign as al
import numpy as np
from PyQt5.QtCore import pyqtSignal
from skimage.transform import SimilarityTransform

from als.code_utilities import log, Timer
from als.model.base import Image
from als.model.data import STACKING_MODE_SUM, STACKING_MODE_MEAN, DYNAMIC_DATA
from als.processing import QueueConsumer

_LOGGER = logging.getLogger(__name__)


class StackingError(Exception):
    """
    Base class for stacking errors
    """


class Stacker(QueueConsumer):
    """
    Responsible of image stacking : alignment and registration
    """

    stack_size_changed_signal = pyqtSignal(int)
    """Qt signal emitted when stack size changed"""

    @log
    def __init__(self, stack_queue):
        QueueConsumer.__init__(self, "Stacker", stack_queue)
        self._size: int = 0
        self._last_stacking_result: Image = None
        self._align_reference: Image = None

    @log
    def reset(self):
        """
        Reset stacker to its starting state : No reference, no result and counter = 0.
        """
        self.size = 0
        self._last_stacking_result = None
        self._align_reference = None

    @log
    def _publish_stacking_result(self, image: Image):
        """
        Record a new stacking result

        :param image: new stacking result
        :type image: Image
        """
        self._last_stacking_result = image
        self.size += 1
        self.new_result_signal.emit(image)

    @property
    def size(self):
        """
        Retrieves the number of stacked images since last reset

        :return: how many images did we stack
        :rtype: int
        """
        return self._size

    @size.setter
    def size(self, size):
        """
        Sets stack size

        :param size: the size
        :type size: int
        """
        self._size = size
        self.stack_size_changed_signal.emit(self.size)

    def _handle_image(self, image: Image):

        if self.size == 0:
            _LOGGER.debug("This is the first image for this stack. Publishing right away")
            self._publish_stacking_result(image)
            self._align_reference = image

        else:
            try:
                if not image.is_same_shape_as(self._last_stacking_result):
                    raise StackingError("Image dimensions or color don't match stack content")

                if DYNAMIC_DATA.align_before_stacking:

                    # alignment is a memory greedy process, we take special care of such errors
                    try:
                        self._align_image(image)
                    except OSError as os_error:
                        raise StackingError(os_error)

                self._stack_image(image, DYNAMIC_DATA.stacking_mode)
                self._publish_stacking_result(image)

            except StackingError as stacking_error:
                _LOGGER.warning(f"Could not stack image {image.origin} : {stacking_error}. Image is DISCARDED")

    @log
    def _align_image(self, image):
        """
        align image with the current align reference

        The image data is modified in place by this function

        :param image: the image to be aligned
        :type image: Image
        """

        with Timer() as find_timer:
            transformation = self._find_transformation(image)
        _LOGGER.debug(f"Found transformation for alignment of {image.origin} in "
                      f"{find_timer.elapsed_in_milli_as_str} ms")

        with Timer() as apply_timer:
            self._apply_transformation(image, transformation)
        _LOGGER.debug(f"Applied transformation for alignment of {image.origin} in "
                      f"{apply_timer.elapsed_in_milli_as_str} ms")

    @log
    def _apply_transformation(self, image: Image, transformation: SimilarityTransform):
        """
        Apply a transformation to an image.

        If image is color, channels are processed using multiprocessing, allowing global operation to take less time on
        a multi core CPU

        Image is modified in place by this function

        :param image: the image to apply transformation to
        :type image: Image

        :param transformation: the transformation to apply
        :type transformation: skimage.transform._geometric.SimilarityTransform
        """
        if image.is_color():
            _LOGGER.debug(f"Aligning color image...")

            manager = Manager()
            results_dict = manager.dict()
            channel_processors = []

            for channel in range(3):
                processor = Process(target=Stacker._apply_single_channel_transformation,
                                    args=[image,
                                          self._last_stacking_result,
                                          transformation,
                                          results_dict,
                                          channel])
                processor.start()
                channel_processors.append(processor)

            for processor in channel_processors:
                processor.join()

            _LOGGER.debug("Color channel processes are done. Fetching results and storing results...")

            for channel, data in results_dict.items():
                image.data[channel] = data

            _LOGGER.debug(f"Aligning color image DONE")

        else:
            _LOGGER.debug(f"Aligning b&w image...")

            result_dict = dict()

            Stacker._apply_single_channel_transformation(
                image,
                self._last_stacking_result,
                transformation,
                result_dict
            )

            image.data = result_dict[0]

            _LOGGER.debug(f"Aligning b&w image : DONE")

    @staticmethod
    @log
    def _apply_single_channel_transformation(image, reference, transformation, results_dict, channel=None):
        """
        apply a transformation on a specific channel (RGB) of a color image, or whole data of a b&w image.

        :param image: the image to apply transformation to
        :type image: Image

        :param reference: the align reference image
        :type reference: Image

        :param transformation: the transformation to apply
        :type transformation: skimage.transform._geometric.SimilarityTransform

        :param results_dict: the dict into which transformation result is to be stored. dict key is the channel number for a
               color image, or 0 for a b&w image
        :type results_dict: dict

        :param channel: the 0 indexed number of the color channel to process (0=red, 1=green, 2=blue)
        :type channel: int
        """

        if channel is not None:
            target_index = channel
            source_data = image.data[channel]
            reference_data = reference.data[channel]
        else:
            target_index = 0
            source_data = image.data
            reference_data = reference.data

        results_dict[target_index] = np.float32(al.apply_transform(transformation, source_data, reference_data))

    @log
    def _find_transformation(self, image: Image):
        """
        Iteratively try and find a valid transformation to align image with stored align reference.

        We perform 3 tries with growing image sizes of a centered image subset : 10%, 30% and 100% of image size

        :param image: the image to be aligned
        :type image: Image

        :return: the found transformation
        :raises: StackingError when no transformation is found using the whole image
        """

        for ratio in [.1, .33, 1.]:

            top, bottom, left, right = self._get_image_subset_boundaries(ratio)

            # pick green channel if image has color
            if image.is_color():
                new_subset = image.data[1][top:bottom, left:right]
                ref_subset = self._align_reference.data[1][top:bottom, left:right]
            else:
                new_subset = image.data[top:bottom, left:right]
                ref_subset = self._align_reference.data[top:bottom, left:right]

            try:
                _LOGGER.debug(f"Searching valid transformation on subset "
                              f"with ratio:{ratio} and shape: {new_subset.shape}")

                transformation, matches = al.find_transform(new_subset, ref_subset)

                _LOGGER.debug(f"Found transformation with subset ratio = {ratio}")
                _LOGGER.debug(f"rotation : {transformation.rotation}")
                _LOGGER.debug(f"translation : {transformation.translation}")
                _LOGGER.debug(f"scale : {transformation.scale}")
                _LOGGER.debug(f"image matched features count : {len(matches[0])}")

                return transformation

            # pylint: disable=W0703
            except Exception as alignment_error:
                # we have no choice but catching Exception, here. That's what AstroAlign raises in some cases
                # this will catch MaxIterError as well...
                if ratio == 1.:
                    raise StackingError(alignment_error)

                _LOGGER.debug(f"Could not find transformation on subset with ratio = {ratio}.")
                continue

    @log
    def _get_image_subset_boundaries(self, ratio: float):
        """
        Retrieves a tuple of 4 int values representing the limits of a centered box (a.k.a. subset) as big as
        ratio * stored stacking result's size

        :param ratio: size ratio of subset vs stacking result
        :type ratio: float

        :return: a tuple of 4 int for top, bottom, left, right
        :rtype: tuple
        """

        width = self._last_stacking_result.width
        height = self._last_stacking_result.height

        horizontal_margin = int((width - (width * ratio)) / 2)
        vertical_margin = int((height - (height * ratio)) / 2)

        left = 0 + horizontal_margin
        right = width - horizontal_margin - 1
        top = 0 + vertical_margin
        bottom = height - vertical_margin - 1

        return top, bottom, left, right

    @log
    def _stack_image(self, image: Image, stacking_mode: str):
        """
        Compute stacking according to user defined stacking mode

        the image data is modified in place by this function

        :param image: the image to be stacked
        :type image: Image

        :param stacking_mode: a string representation of the desired stacking mode
        :type stacking_mode: str
        """

        with Timer() as registering_timer:

            if stacking_mode == STACKING_MODE_SUM:
                image.data = image.data + self._last_stacking_result.data
            elif stacking_mode == STACKING_MODE_MEAN:
                image.data = (self.size * self._last_stacking_result.data + image.data) / (self.size + 1)
            else:
                raise StackingError(f"Unsupported stacking mode : {stacking_mode}")

        _LOGGER.info(f"Done stacking {image.origin} in {registering_timer.elapsed_in_milli_as_str} ms")
