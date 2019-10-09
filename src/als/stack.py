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
from multiprocessing import Process

import astroalign as al
from PyQt5.QtCore import QThread, pyqtSignal
from skimage.transform import SimilarityTransform

from als.code_utilities import log, Timer
from als.model import Image, SignalingQueue, STORE, STACKING_MODE_SUM, STACKING_MODE_MEAN

_LOGGER = logging.getLogger(__name__)


class StackingError(Exception):
    """
    Base class for stacking errors
    """


class Stacker(QThread):
    """
    Responsible of image stacking : alignment and registration
    """

    stack_size_changed_signal = pyqtSignal(int)
    stack_result_ready_signal = pyqtSignal()

    @log
    def __init__(self, stack_queue):
        QThread.__init__(self)
        self._stack_queue: SignalingQueue = stack_queue
        self._counter: int = 0
        self._stop_asked: bool = False
        self._result: Image = None
        self._align_reference = None

    @log
    def reset(self):
        """
        Reset stacker to its starting state : No reference and counter = 0.
        """
        self._counter = 0
        self._result = None
        self._align_reference = None
        self.stack_size_changed_signal.emit(self.size)

    @log
    def _publish_stacking_result(self, image: Image):
        self._result = image
        self._result.origin = "Stack reference"
        self._counter += 1
        self.stack_size_changed_signal.emit(self.size)

        STORE.stacking_result = self._result
        self.stack_result_ready_signal.emit()

    @property
    def size(self):
        """
        Retrieves the number of stacked images since last reset

        :return: how many images did we stack
        :rtype: int
        """
        return self._counter

    @log
    def run(self):
        """
        Performs all stacking duties :

         - Get new image from queue
         - Align image if asked for
         - Register image in stack
         - publish resulting image
        """
        while not self._stop_asked:

            if self._stack_queue.qsize() > 0:

                image = self._stack_queue.get()

                _LOGGER.info(f"Start stacking image {image.origin}")

                with Timer() as stacking_timer:

                    if self.size == 0:
                        self._publish_stacking_result(image)
                        self._align_reference = image

                    else:
                        try:
                            if not image.is_same_shape_as(self._result):
                                raise StackingError(f"Image dimensions or color don't match stack content")

                            if STORE.align_before_stacking:
                                self._align_image(image)

                            self._register_image(image, STORE.stacking_mode)
                            self._publish_stacking_result(image)

                        except StackingError as stacking_error:
                            self._report_error(image, stacking_error)

                _LOGGER.info(f"Done stacking image in "
                             f"{stacking_timer.elapsed_in_milli_as_str} ms")

            self.msleep(20)

    @log
    def _align_image(self, image):

        with Timer() as transformation_find_timer:
            transformation = self._find_transformation(image)
        _LOGGER.info(f"Computed transformation for alignment of {image.origin} in "
                     f"{transformation_find_timer.elapsed_in_milli_as_str} ms")

        with Timer() as transformation_apply_timer:
            self._apply_transformation(image, transformation)
        _LOGGER.info(f"Applied transformation for alignment of {image.origin} in "
                     f"{transformation_apply_timer.elapsed_in_milli_as_str} ms")

    @log
    def _apply_transformation(self, image: Image, transformation: SimilarityTransform):

        if image.is_color():
            _LOGGER.debug(f"Aligning color image...")

            channel_processors = []

            for channel in range(3):
                processor = Process(target=Stacker._apply_single_channel_transformation,
                                    args=[image,
                                          self._result,
                                          transformation,
                                          channel])
                processor.start()
                channel_processors.append(processor)

            for processor in channel_processors:
                processor.join()

            _LOGGER.debug(f"Aligning color image DONE")

        else:
            _LOGGER.debug(f"Aligning b&w image...")
            self._apply_single_channel_transformation(
                image,
                self._result,
                transformation
            )
            _LOGGER.debug(f"Aligning b&w image : DONE")

    @staticmethod
    @log
    def _apply_single_channel_transformation(image, reference, transformation, channel=None):

        if channel is not None:
            image.data[channel] = al.apply_transform(
                transformation,
                image.data[channel],
                reference.data[channel])

        else:
            image.data = al.apply_transform(
                transformation,
                image.data,
                reference.data)

    @log
    def _find_transformation(self, image: Image):

        for ratio in [.1, .33, 1.]:

            top, bottom, left, right = self._get_image_subset_bounds(ratio)

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
                _LOGGER.debug(f"image feature matches : {len(matches[0])}")

                return transformation

            # pylint: disable=W0703
            except Exception as alignment_error:
                # we have no choice but catching Exception, here. That's what AstroAlign raises in some cases
                # this will take care of MaxIterError as well...
                if ratio == 1.:
                    raise StackingError(alignment_error)

                _LOGGER.debug(f"Could not find transformation on subset with ratio = {ratio}.")
                continue

    @log
    def _get_image_subset_bounds(self, ratio: float):

        width = self._result.width
        height = self._result.height

        horizontal_margin = int((width - (width * ratio)) / 2)
        vertical_margin = int((height - (height * ratio)) / 2)

        left = 0 + horizontal_margin
        right = width - horizontal_margin - 1

        top = 0 + vertical_margin
        bottom = height - vertical_margin - 1

        return top, bottom, left, right

    @log
    def _register_image(self, image, stacking_mode: str):

        with Timer() as registering_timer:

            if stacking_mode == STACKING_MODE_SUM:
                image.data = image.data + self._result.data
            elif stacking_mode == STACKING_MODE_MEAN:
                image.data = (self.size * self._result.data + image.data) / (self.size + 1)
            else:
                raise StackingError(f"Unsupported stacking mode : {stacking_mode}")

        _LOGGER.info(f"Done {stacking_mode}-registering {image.origin} in "
                     f"{registering_timer.elapsed_in_milli_as_str} ms")

    # pylint: disable=R0201
    @log
    def _report_error(self, image, error):
        _LOGGER.warning(f"Could not stack image {image.origin} : {error}")

    @log
    def stop(self):
        """
        Flips a flag used to end the main thread loop
        """
        self._stop_asked = True
        self.wait()
        _LOGGER.info("Stacker stopped")
