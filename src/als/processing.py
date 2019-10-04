"""
Provides all means of image processing
"""
import logging
from abc import abstractmethod
from queue import Queue

import cv2
from PyQt5.QtCore import QThread
from als.code_utilities import log, Timer
from als.model import Image

_LOGGER = logging.getLogger(__name__)


class ProcessingError(Exception):
    """
    Must be raised in case of processing error.
    """


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


class ImageDebayer(ImageProcessor):
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
            image.bayer_pattern = None

        return image


class PreProcessPipeline(QThread):
    """
    Responsible of grabbing images from the input queue and applying a set of pre-processing units to each one, before
    pushing it to the stacking queue.
    """

    @log
    def __init__(self, input_queue: Queue):
        QThread.__init__(self)
        self._stop_asked = False
        self._input_queue = input_queue

        self._processors = [ImageDebayer(), ]

    @log
    def run(self):
        """
        Starts polling the input queue and perform pre-processing units to each image popped from the input queue

        If any processing error occurs, the current image is dropped
        """
        while not self._stop_asked:

            if self._input_queue.qsize() > 0:
                image = self._input_queue.get()

                try:
                    for processor in self._processors:

                        with Timer() as code_timer:
                            image = processor.process_image(image)

                        _LOGGER.info(f"Applied process '{processor.__class__.__name__}' to {image.origin} : "
                                     f"in {code_timer.elapsed_in_milli_as_str} ms")
                    # TODO : push image to stacker

                except ProcessingError as processing_error:
                    _LOGGER.error(f"Error applying process '{processor.__class__.__name__}' to {image} : "
                                  f"{processing_error} *** "
                                  f"Image will be ignored")

            self.msleep(20)

    @log
    def stop(self):
        """
        Sets flag that will interrupt the main loop in run()
        """
        self._stop_asked = True
