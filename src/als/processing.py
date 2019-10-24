"""
Provides all means of image processing
"""
import logging
from abc import abstractmethod
from typing import List

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from skimage import exposure

from als.code_utilities import log, Timer, SignalingQueue
from als.model.base import Image
from als.model.params import ProcessingParameter, RangeParameter, SwitchParameter, ListParameter

_LOGGER = logging.getLogger(__name__)


class ProcessingError(Exception):
    """
    Must be raised in case of processing error.
    """


# pylint: disable=R0903
class ImageProcessor:
    """
    Base abstract class for all image processors, regardless of what pipeline they are used in

    Subclasses must implement a single method : process_image(image: Image)
    """

    @log
    def __init__(self):
        self._parameters = list()

    @log
    def get_parameters(self) -> List[ProcessingParameter]:
        """
        Gets processes parameters

        :return: the parameters
        :rtype: List[ProcessingParameter]
        """
        return self._parameters

    @abstractmethod
    def process_image(self, image: Image):
        """
        Perform  image processing specific to this class

        :param image: the image to process
        :type image: Image

        :raises: ProcessingError - an error occurred while processing image

        :return: the processed image
        :rtype: Image
        """


class Levels(ImageProcessor):
    """Implements levels processing"""

    _UPPER_LIMIT = 2**16 - 1

    @log
    def __init__(self):
        super().__init__()

        self._parameters.append(
            SwitchParameter(
                "autostretch",
                "automatic histogram stretch",
                default=True))

        self._parameters.append(
            ListParameter(
                "stretch method",
                "autostretch method",
                default='Contrast',
                choices=['Contrast', 'Adaptive']))

        self._parameters.append(
            RangeParameter(
                "black",
                "black level",
                default=0,
                minimum=0,
                maximum=Levels._UPPER_LIMIT))

        self._parameters.append(
            RangeParameter(
                "mids",
                "midtones level",
                default=1,
                minimum=0,
                maximum=2))

        self._parameters.append(
            RangeParameter(
                "white",
                "while level",
                default=Levels._UPPER_LIMIT,
                minimum=0,
                maximum=Levels._UPPER_LIMIT))

    @log
    def process_image(self, image: Image):
        # pylint: disable=R0914

        auto_stretch = self._parameters[0]
        stretch_method = self._parameters[1]
        black = self._parameters[2]
        midtones = self._parameters[3]
        white = self._parameters[4]

        for param in self._parameters:
            _LOGGER.debug(f"Levels param {param.name} = {param.value}")

        # autostretch
        if auto_stretch.value:
            _LOGGER.debug("Performing Autostretch...")
            image.data = np.interp(image.data,
                                   (image.data.min(), image.data.max()),
                                   (0, Levels._UPPER_LIMIT))

            def histo_adpative_equalization(data):
                return exposure.equalize_adapthist(np.uint16(data), nbins=Levels._UPPER_LIMIT + 1, clip_limit=.01)

            def contrast_stretching(data):
                low, high = np.percentile(data, (2, 98))
                return exposure.rescale_intensity(data, in_range=(low, high))

            available_stretches = [histo_adpative_equalization, contrast_stretching]

            chosen_stretch = available_stretches[stretch_method.choices.index(stretch_method.value)]

            if image.is_color():
                for channel in range(3):
                    image.data[channel] = chosen_stretch(image.data[channel])
            else:
                image.data = chosen_stretch(image.data)
            _LOGGER.debug("Autostretch Done")

            # autostretch output range is [0, 1]
            # so we remap values to our range [0, Levels._UPPER_LIMIT]
            image.data *= Levels._UPPER_LIMIT

        # midtones correction
        do_midtones = not midtones.is_default()
        _LOGGER.debug(f"Levels : do midtones adjustments : {do_midtones}")

        if do_midtones:
            _LOGGER.debug("Performing midtones adjustments...")
            corrected_midtones_value = self._compute_midtones_value()
            image.data = Levels._UPPER_LIMIT * image.data ** (1 / corrected_midtones_value) / Levels._UPPER_LIMIT ** (
                1 / corrected_midtones_value)
            _LOGGER.debug("Midtones level adjustments Done")

        # black / white levels
        do_black_white_levels = not black.is_default() or not white.is_default()
        _LOGGER.debug(f"Levels : do black and white adjustments : {do_black_white_levels}")

        if do_black_white_levels:
            _LOGGER.debug("Performing black / white level adjustments...")
            image.data = np.clip(image.data, black.value, white.value)
            _LOGGER.debug("Black / white level adjustments Done")

        # final interpolation
        image.data = np.float32(np.interp(image.data,
                                          (image.data.min(), image.data.max()),
                                          (0, Levels._UPPER_LIMIT)))

        return image

    def _compute_midtones_value(self):
        """
        Modify midtone param value using a custom transfer function.

        actual midtone param (input) has a range of [0, 2]

        transfer function has the following properties :

          - f(0) = 0.1
          - for x in ]0, 1] : f(x) = x
          - for x in ]1, 2] :
            - if autostretch is off : f(x) = 10x
            - if autostretch is on  : f(x) = 2x

        :return: the computed midtones param value
        :rtype: float
        """

        auto_stretch_on = self._parameters[0].value
        mids_level = self._parameters[3].value

        if auto_stretch_on:
            slope = 2
        else:
            slope = 10

        if mids_level < 0 or mids_level > 2:
            raise ProcessingError(f"Invalid value for midtones input value : {mids_level}")

        if mids_level == 0:
            return 0.1

        if mids_level <= 1:
            return mids_level

        return slope * mids_level


# pylint: disable=R0903
class Standardize(ImageProcessor):
    """
    Make image data structure conform to all processing needs.

    Here are the aspects we enforce :

      #. data array of color (debayered) images have color as the first axis. So a typical shape for a color image would
         be : (3, y, x).

      #. each array element is of type float32

    """
    @log
    def process_image(self, image: Image):

        if image.is_color():
            image.set_color_axis_as(0)

        image.data = np.float32(image.data)

        return image


# pylint: disable=R0903
class Debayer(ImageProcessor):
    """
    Provides image debayering.
    """

    @log
    def process_image(self, image: Image):

        if image.needs_debayering():

            bayer_pattern = image.bayer_pattern

            cv2_debayer_dict = {

                "BG": cv2.COLOR_BAYER_BG2RGB,
                "GB": cv2.COLOR_BAYER_GB2RGB,
                "RG": cv2.COLOR_BAYER_RG2RGB,
                "GR": cv2.COLOR_BAYER_GR2RGB
            }

            cv_debay = bayer_pattern[3] + bayer_pattern[2]

            try:
                debayered_data = cv2.cvtColor(image.data, cv2_debayer_dict[cv_debay])
            except KeyError:
                raise ProcessingError(f"unsupported bayer pattern : {bayer_pattern}")

            image.data = debayered_data

        return image


class ConvertForOutput(ImageProcessor):
    """
    Moves colors data to 3rd array axis for color images and reduce data range to unsigned 16 bits
    """
    @log
    def process_image(self, image: Image):

        if image.is_color():
            image.set_color_axis_as(2)

        image.data = np.uint16(np.clip(image.data, 0, 2 ** 16 - 1))

        return image


class QueueConsumer(QThread):
    """
    Abstract class for all our queue consumers.

    Responsible of grabbing images from a queue

    actual processing payload is to be implemented in the following abstract method : _handle_image().
    """

    new_result_signal = pyqtSignal(Image)
    """Qt signal to emit when a new image has been processed"""

    busy_signal = pyqtSignal()
    """Qt signal to emit when an image has been retrieved and we are about to process it"""

    waiting_signal = pyqtSignal()
    """Qt signal to emit when image processing is complete"""

    @log
    def __init__(self, name: str, queue: SignalingQueue):
        QThread.__init__(self)
        self._stop_asked = False
        self._name = name
        self._queue = queue

    @abstractmethod
    @log
    def _handle_image(self, image: Image):
        """
        Perform hopefully useful actions on image

        :param image: the image to handle
        :type image: Image
        """

    @log
    def run(self):
        """
        Starts polling the queue and perform processing units to each image

        If any processing error occurs, the current image is dropped
        """
        while not self._stop_asked:

            if self._queue.qsize() > 0:

                self.busy_signal.emit()
                image = self._queue.get()
                _LOGGER.info(f"Start {self._name} on {image.origin}")

                with Timer() as timer:
                    self._handle_image(image)

                _LOGGER.info(f"End {self._name} on {image.origin} in {timer.elapsed_in_milli_as_str} ms")
                self.waiting_signal.emit()

            self.msleep(20)

    @log
    def stop(self):
        """
        Sets flag that will interrupt the main loop in run()
        """
        self._stop_asked = True
        _LOGGER.info(f"{self._name} stopped")


class Pipeline(QueueConsumer):
    """
    QueueConsumer specialization allowing to apply a list of image processors to each image
    """

    @log
    def __init__(self, name: str, queue: SignalingQueue, final_processes: list):
        QueueConsumer.__init__(self, name, queue)
        self._processes = []
        self._final_processes = final_processes

    def _handle_image(self, image: Image):

        try:
            for processor in self._processes + self._final_processes:
                image = processor.process_image(image)

            self.new_result_signal.emit(image)

        except ProcessingError as processing_error:
            _LOGGER.warning(
                f"Error applying process '{processor.__class__.__name__}' to image {image} : "
                f"{processing_error} *** "
                f"Image will be ignored")

    @log
    def add_process(self, process: ImageProcessor):
        """
        Add an image processor to the list of processes to run on images

        :param process: the processor to add
        :type process: ImageProcessor
        """
        self._processes.append(process)
