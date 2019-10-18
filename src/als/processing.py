"""
Provides all means of image processing
"""
import logging
from abc import abstractmethod

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from als.code_utilities import log, Timer
from als.model import Image, SignalingQueue

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

        image.data = np.uint16(np.where(image.data < 2 ** 16 - 1, image.data, 2 ** 16 - 1))

        return image


class Pipeline(QThread):
    """
    Responsible of grabbing images from a queue and applying a set of processing units to each one
    """

    new_result_signal = pyqtSignal(Image)
    """Qt signal to emit when a new image has been processed"""

    @log
    def __init__(self, name: str, queue: SignalingQueue, final_processes: list):
        QThread.__init__(self)
        self._stop_asked = False
        self._name = name
        self._queue = queue
        self._processes = []
        self._final_processes = final_processes

    @log
    def run(self):
        """
        Starts polling the queue and perform processing units to each image

        If any processing error occurs, the current image is dropped
        """
        while not self._stop_asked:

            if self._queue.qsize() > 0:
                image = self._queue.get()

                _LOGGER.info(f"Start {self._name} on image {image.origin}")

                try:
                    with Timer() as image_timer:

                        for processor in self._processes + self._final_processes:
                            image = processor.process_image(image)

                    _LOGGER.info(f"End {self._name} on image {image.origin} "
                                 f"in {image_timer.elapsed_in_milli_as_str} ms")

                    self.new_result_signal.emit(image)

                except ProcessingError as processing_error:
                    _LOGGER.warning(
                        f"Error applying process '{processor.__class__.__name__}' to image {image} : "
                        f"{processing_error} *** "
                        f"Image will be ignored")

            self.msleep(20)

    @log
    def stop(self):
        """
        Sets flag that will interrupt the main loop in run()
        """
        self._stop_asked = True
        self.wait()
        _LOGGER.info("PreProcess pipeline stopped")

    @log
    def add_process(self, process: ImageProcessor):
        """
        Add an image processor to the list of processes to run on images

        :param process: the processor to add
        :type process: ImageProcessor
        """
        self._processes.append(process)
