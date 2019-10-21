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
from als.model.params import ProcessingParameter, RangeParameter, SwitchParameter

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

        self._parameters.append(RangeParameter("black", "black level",
                                               0, 0, 0, Levels._UPPER_LIMIT))

        self._parameters.append(RangeParameter("white", "while level",
                                               Levels._UPPER_LIMIT, Levels._UPPER_LIMIT, 0, Levels._UPPER_LIMIT))

        self._parameters.append(SwitchParameter("autostretch",
                                                "automatic histogram stretch", True, True))

    @log
    def process_image(self, image: Image):

        black_level = self._parameters[0]
        white_level = self._parameters[1]
        auto_stretch = self._parameters[2]

        if auto_stretch.value:

            image.data = np.interp(image.data,
                                   (image.data.min(), image.data.max()),
                                   (0, Levels._UPPER_LIMIT))

            if image.is_color():
                for index in range(3):

                    image.data[index] = exposure.equalize_adapthist(
                        np.uint16(image.data[index]),
                        nbins=Levels._UPPER_LIMIT+1,
                        clip_limit=.01)
            else:
                image.data = exposure.equalize_adapthist(
                    np.uint16(image.data),
                    nbins=Levels._UPPER_LIMIT+1,
                    clip_limit=.01)

            # autostretch outputs an image with value range = [0, 1]
            image.data *= Levels._UPPER_LIMIT

        image.data = np.clip(image.data, black_level.value, white_level.value)

        image.data = np.interp(image.data,
                               (image.data.min(), image.data.max()),
                               (0, Levels._UPPER_LIMIT))

        return image


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

        # TODO : use numpy clip or imp, here
        image.data = np.uint16(np.where(image.data < 2 ** 16 - 1, image.data, 2 ** 16 - 1))

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
                _LOGGER.info(f"Start {self._name} on image {image.origin}")

                with Timer() as timer:
                    self._handle_image(image)

                _LOGGER.info(f"End {self._name} on image {image.origin} in {timer.elapsed_in_milli_as_str} ms")
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
