"""
Everything we need to perform outputs from ALS

For now, we only save some images to disk, but who knows...
"""
import logging
from queue import Queue

import cv2
import numpy
from PyQt5.QtCore import QThread, pyqtSignal

from als import config
from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)

# queue to which are posted all image save commands
_IMAGE_SAVE_QUEUE = Queue()


class ImageSaver(QThread):
    """
    Saves images according to commands posted to IMAGE_SAVE_QUEUE in its own thread

    """

    save_successful_signal = pyqtSignal(str)
    save_fail_signal = pyqtSignal([str, str])

    @log
    def __init__(self):
        super().__init__()
        self._stop_asked = False

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
        while not self._stop_asked or not _IMAGE_SAVE_QUEUE.empty():
            if not _IMAGE_SAVE_QUEUE.empty():
                image_save_command = _IMAGE_SAVE_QUEUE.get_nowait()
                self._save_image(image_save_command)
            self.msleep(100)

    @log
    def stop(self):
        """
        Sets a flag that will interrupt the main loop in run()
        """
        _LOGGER.info("Stopping image saver")
        queue_size = _IMAGE_SAVE_QUEUE.qsize()
        if queue_size > 0:
            _LOGGER.warning(f"There are still {queue_size} images waiting to be saved. Saving them all...")
        self._stop_asked = True

    @log
    def _save_image(self, save_command_dict):
        """
        Saves image to work folder

        :param save_command_dict: all infos needed to save an image
        :type save_command_dict: a dict, with 2 keys :

          - 'image' (Image) : the image data
          - 'treport_on_failure' (bool)   : Do we report save failures ?
        """

        image = save_command_dict['image']
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
            if save_command_dict['report_on_failure']:
                self.save_fail_signal.emit(target_path, failure_details)

    @staticmethod
    @log
    def _save_image_as_tiff(image, target_path):
        """
        Saves image as tiff.

        :param image: the image to save
        :type image: numpy.Array

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
    def _save_image_as_png(image, target_path):
        """
        Saves image as png.

        :param image: the image to save
        :type image: numpy.Array

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
    def _save_image_as_jpg(image, target_path):
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
        if image.data.dtype == "uint16":
            bit_depth = 16
        else:
            bit_depth = 8

        if bit_depth > 8:
            image.data = (image.data / (((2 ** bit_depth) - 1) / ((2 ** 8) - 1))).astype('uint8')

        return cv2.imwrite(target_path,
                           cv2.cvtColor(image.data, cv2.COLOR_RGB2BGR),
                           [int(cv2.IMWRITE_JPEG_QUALITY), 90]), ''


@log
def save_image(image, image_save_format, target_folder, file_name_base, report_on_failure=False):
    """
    Saves an image to disk.

    Image is pushed to a queue polled by a worker thread

    :param image: the image to save
    :type image: Image

    :param image_save_format: image file format specifier
    :type image_save_format: str

    :param target_folder: path to target folder
    :type target_folder: str

    :param file_name_base: filename base (without extension)
    :type file_name_base: str

    :param report_on_failure: ask worker thread to report save failure
    :type report_on_failure: bool
    """
    image.destination = target_folder + "/" + file_name_base + '.' + image_save_format

    _IMAGE_SAVE_QUEUE.put({'image': image.clone(),
                           'report_on_failure': report_on_failure})
