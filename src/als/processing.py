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


class PreProcessPipeline(QThread):
    """
    Responsible of grabbing images from the pre-process queue and applying a set of pre-processing units to each one
    """

    new_result_signal = pyqtSignal(Image)
    """Qt signal to emit when a new image has been pre-processed"""

    @log
    def __init__(self, pre_process_queue: SignalingQueue):
        QThread.__init__(self)
        self._stop_asked = False
        self._pre_process_queue = pre_process_queue
        self._pre_processes = []
        self._pre_processes.extend([Debayer(), Standardize()])

    @log
    def run(self):
        """
        Starts polling the pre-process queue and perform pre-processing units to each image

        If any processing error occurs, the current image is dropped
        """
        while not self._stop_asked:

            if self._pre_process_queue.qsize() > 0:
                image = self._pre_process_queue.get()

                _LOGGER.info(f"Start pre-processing image : {image.origin}")

                try:
                    with Timer() as image_timer:

                        for processor in self._pre_processes:

                            with Timer() as process_timer:
                                image = processor.process_image(image)

                            _LOGGER.info(
                                f"Applied process '{processor.__class__.__name__}' to image {image.origin} : "
                                f"in {process_timer.elapsed_in_milli_as_str} ms")

                    _LOGGER.info(f"Done pre-processing image {image.origin}"
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


class PostProcessPipeline(QThread):
    """
    Responsible of grabbing images from the process queue and applying a set of post-processing units to each one,
    before storing it into the dynamic data store
    """

    new_processing_result_signal = pyqtSignal(Image)
    """Qt signal emitted when an new processing result is ready"""

    @log
    def __init__(self, process_queue: SignalingQueue):
        QThread.__init__(self)
        self._stop_asked = False
        self._process_queue = process_queue
        self._processes = []
        self._processes_done_last = [ConvertForOutput()]

    @log
    def run(self):
        """
        Starts polling the process queue and perform post-processing units to each image popped from the queue

        If any processing error occurs, the current image is dropped
        """
        while not self._stop_asked:

            if self._process_queue.qsize() > 0:

                image = self._process_queue.get()

                # we make sure we work on the latest stack result, dropping older images if needed
                while self._process_queue.qsize() > 0:
                    image = self._process_queue.get()

                image = image.clone()

                _LOGGER.info(f"Start post-processing image : {image.origin}")

                for processor in self._processes + self._processes_done_last:

                    try:
                        with Timer() as code_timer:
                            image = processor.process_image(image)

                        _LOGGER.info(
                            f"Applied process '{processor.__class__.__name__}' to image {image.origin} : "
                            f"in {code_timer.elapsed_in_milli_as_str} ms")

                    except ProcessingError as processing_error:
                        _LOGGER.warning(
                            f"Error applying process '{processor.__class__.__name__}' to image {image} : "
                            f"{processing_error} *** "
                            f"Image will be ignored")
                        break

                _LOGGER.info(f"Done post-processing image : {image.origin}")

                image.origin = "Post Processing Result"
                self.new_processing_result_signal.emit(image)

            self.msleep(20)

    @log
    def stop(self):
        """
        Sets flag that will interrupt the main loop in run()
        """
        self._stop_asked = True
        self.wait()
        _LOGGER.info("PostProcess pipeline stopped")
