"""
Everything we need to perform outputs from ALS

For now, we only save some images to disk, but who knows...
"""
import logging
from queue import Queue

import cv2
from PyQt5.QtCore import QThread, pyqtSignal

from astropy.io import fits

from als import config
from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)

# queue to which are posted all image save commands
_IMAGE_SAVE_QUEUE = Queue()


class ImageSaveCommand:
    """
    Represents an image save command.

    It encapsulated the image itself, the filename to save to and the target folder
    """

    @log
    def __init__(self, image, target_path):
        """
        Creates a new ImageSaveCommand.

        :param image: the image to save
        :type image: numpy.Array

        :param target_path: absolute path of the file to save image to
        :type target_path: str
        """
        self._image = image
        self._target_path = target_path

    @log
    def get_image(self):
        """
        Retrieves image data.

        :return: the image data
        :rtype: numpy.Array
        """
        return self._image

    @log
    def get_target_path(self):
        """
        Retrieves target path.

        :return: absolute path of the file to save image to
        :rtype: str
        """
        return self._target_path


class ImageSaver(QThread):
    """
    Saves images according to commands posted to IMAGE_SAVE_QUEUE in its own thread

    """

    save_successful_signal = pyqtSignal(str)
    save_fail_signal = pyqtSignal(str)

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
    def _save_image(self, command):
        """
        Saves image to work folder

        :param command: the image save command
        :type command: ImageSaveCommand
        """

        target_path = command.get_target_path()

        if target_path.endswith(config.IMAGE_SAVE_TIFF):
            save_successful, details = ImageSaver._save_image_as_tiff(command.get_image(), target_path)

        elif target_path.endswith(config.IMAGE_SAVE_PNG):
            save_successful, details = ImageSaver._save_image_as_png(command.get_image(), target_path)

        elif target_path.endswith(config.IMAGE_SAVE_JPEG):
            save_successful, details = ImageSaver._save_image_as_jpg(command.get_image(), target_path)

        elif target_path.endswith(config.IMAGE_SAVE_FIT):
            save_successful, details = ImageSaver._save_image_as_fit(command.get_image(), target_path)

        else:
            # Unsupported format in config file. Should never happen
            save_successful, details = False, f"Unsupported File format for {target_path}"

        if save_successful:
            message = f"Successful image save : {target_path}"
            _LOGGER.info(message)
            self.save_successful_signal.emit(message)

        else:
            message = f"ERROR, Failed to save image {target_path}. "
            if details.strip():
                message += details
            _LOGGER.error(message)
            self.save_fail_signal.emit(message)

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

        As we are using cv2.imwrite, we won't get any details on failures
        """

        return cv2.imwrite(target_path, image), ""

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

        As we are using cv2.imwrite, we won't get any details on failures
        """

        return cv2.imwrite(target_path,
                           image,
                           [cv2.IMWRITE_PNG_COMPRESSION, 9]), ""

    @staticmethod
    @log
    def _save_image_as_jpg(image, target_path):
        """
        Saves image as jpg.

        :param image: the image to save
        :type image: numpy.Array

        :param target_path: the absolute path of the image file to save to
        :type target_path: str

        :return: a tuple with 2 values :

          - True if save succeeded, False otherwise
          - Details on cause of save failure, if occurs

        As we are using cv2.imwrite, we won't get any details on failures
        """

        image_to_save = image
        if image_to_save.dtype == "uint16":
            bit_depth = 16
        else:
            bit_depth = 8

        if bit_depth > 8:
            image_to_save = (image_to_save / (((2 ** bit_depth) - 1) / ((2 ** 8) - 1))).astype('uint8')

        return cv2.imwrite(target_path,
                           image_to_save,
                           [int(cv2.IMWRITE_JPEG_QUALITY), 90]), ''

    @staticmethod
    @log
    def _save_image_as_fit(image, target_path):
        """
        Saves image as fit.

        :param image: the image to save
        :type image: numpy.Array

        :param target_path: the absolute path of the image file to save to
        :type target_path: str

        :return: a tuple with 2 values :

          - True if save succeeded, False otherwise
          - Details on cause of save failure, if occurs
        """

        hdu = fits.PrimaryHDU(data=image)

        try:
            hdu.writeto(target_path)
            return True, ''

        except OSError as os_error:
            return False, str(os_error)


@log
def save_image(image_data, image_save_format, target_folder, file_name_base):
    """
    Saves an image to disk.

    :param image_data: the image data
    :type image_data: numpy.Array

    :param image_save_format: image file format specifier
    :type image_save_format: str

    :param target_folder: path to target folder
    :type target_folder: str

    :param file_name_base: filename base (without extension)
    :type file_name_base: str
    """
    target_path = target_folder + "/" + file_name_base + '.' + image_save_format
    _IMAGE_SAVE_QUEUE.put(ImageSaveCommand(image_data, target_path))
