"""
Everything we need to perform outputs from ALS

For now, we only save some images to disk, but who knows...
"""
import logging

import cv2
from PyQt5.QtCore import QThread
from als import config
from als.code_utilities import log
from als.model import Image, SignalingQueue

_LOGGER = logging.getLogger(__name__)


class ImageSaver(QThread):
    """
    Saves images according to commands posted to IMAGE_SAVE_QUEUE in its own thread

    """
    @log
    def __init__(self, save_queue: SignalingQueue):
        super().__init__()
        self._stop_asked = False
        self._save_queue = save_queue

    @log
    def run(self):
        """
        Performs usual duty : Saving images to disk
        """
        # we keep polling the queue in 2 cases :
        #
        # - we have not been asked to stop, regardless of queue content
        # OR
        # - we have been asked to stop, and queue is not empty yet

        while not self._stop_asked or not self._save_queue.empty():
            if not self._save_queue.empty():
                image = self._save_queue.get_nowait()
                ImageSaver._save_image(image)
            self.msleep(100)

    @log
    def stop(self):
        """
        Sets a flag that will interrupt the main loop in run()
        """
        _LOGGER.info("Stopping image saver")
        queue_size = self._save_queue.qsize()
        if queue_size > 0:
            _LOGGER.warning(f"There are still {queue_size} images waiting to be saved. Saving them all...")
        self._stop_asked = True

    @staticmethod
    @log
    def _save_image(image):
        """
        Saves image to disk

        :param image: the image to save
        :type image: Image
        """
        target_path = image.destination

        if target_path.endswith('.' + config.IMAGE_SAVE_TIFF):
            save_is_successful, failure_details = ImageSaver._save_image_as_tiff(image, target_path)

        elif target_path.endswith('.' + config.IMAGE_SAVE_PNG):
            save_is_successful, failure_details = ImageSaver._save_image_as_png(image, target_path)

        elif target_path.endswith('.' + config.IMAGE_SAVE_JPEG):
            save_is_successful, failure_details = ImageSaver._save_image_as_jpg(image, target_path)

        else:
            # Unsupported format in config file. Should never happen
            save_is_successful, failure_details = False, f"Unsupported File format for {target_path}"

        if save_is_successful:
            message = f"Image saved : {target_path}"
            _LOGGER.info(message)

        else:
            message = f"Failed to save image : {target_path}"
            if failure_details.strip():
                message += ' : ' + failure_details
            _LOGGER.error(message)

    @staticmethod
    @log
    def _save_image_as_tiff(image: Image, target_path: str):
        """
        Saves image as tiff.

        :param image: the image to save
        :type image: Image

        :param target_path: the absolute path of the image file to save to
        :type target_path: str

        :return: a tuple with 2 values :

          - True if save succeeded, False otherwise
          - Details on cause of save failure, if occurs

        As we are using cv2.imwrite, we won't get any details on failures. So failure details will always
        be the empty string.
        """
        return cv2.imwrite(target_path, cv2.cvtColor(image.data, cv2.COLOR_RGB2BGR)), ""

    @staticmethod
    @log
    def _save_image_as_png(image: Image, target_path: str):
        """
        Saves image as png.

        :param image: the image to save
        :type image: Image

        :param target_path: the absolute path of the image file to save to
        :type target_path: str

        :return: a tuple with 2 values :

          - True if save succeeded, False otherwise
          - Details on cause of save failure, if occurs

        As we are using cv2.imwrite, we won't get any details on failures. So failure details will always
        be the empty string.
        """
        return cv2.imwrite(target_path,
                           cv2.cvtColor(image.data, cv2.COLOR_RGB2BGR),
                           [cv2.IMWRITE_PNG_COMPRESSION, 9]), ""

    @staticmethod
    @log
    def _save_image_as_jpg(image: Image, target_path: str):
        """
        Saves image as jpg.

        :param image: the image to save
        :type image: Image

        :param target_path: the absolute path of the image file to save to
        :type target_path: str

        :return: a tuple with 2 values :

          - True if save succeeded, False otherwise
          - Details on cause of save failure, if occurs

        As we are using cv2.imwrite, we won't get any details on failures. So failure details will always
        be the empty string.
        """
        # here we are sure that image data type us unsigned 16 bits. We need to downscale to 8 bits
        image.data = (image.data / (((2 ** 16) - 1) / ((2 ** 8) - 1))).astype('uint8')

        return cv2.imwrite(target_path,
                           cv2.cvtColor(image.data, cv2.COLOR_RGB2BGR),
                           [int(cv2.IMWRITE_JPEG_QUALITY), 90]), ''
