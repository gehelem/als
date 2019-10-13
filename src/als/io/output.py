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

          - 'image' (numpy.Array) : the image data
          - 'target_path' (str)   : the absolute path of the file to save to
        """

        target_path = save_command_dict['target_path']
        image = _set_color_axis_as(2, save_command_dict['image'])

        im_type = image.dtype.name
        # filter excess value > limit
        if im_type == 'uint8':
            image = numpy.uint8(numpy.where(image < 2 ** 8 - 1, image, 2 ** 8 - 1))
        elif im_type == 'uint16':
            image = numpy.uint16(numpy.where(image < 2 ** 16 - 1, image, 2 ** 16 - 1))

        if image.ndim > 2:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

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

        As we are using cv2.imwrite, we won't get any details on failures. So failure details will always
        be the empty string.
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

        As we are using cv2.imwrite, we won't get any details on failures. So failure details will always
        be the empty string.
        """
        if image.dtype == "uint16":
            bit_depth = 16
        else:
            bit_depth = 8

        if bit_depth > 8:
            image = (image / (((2 ** bit_depth) - 1) / ((2 ** 8) - 1))).astype('uint8')

        return cv2.imwrite(target_path,
                           image,
                           [int(cv2.IMWRITE_JPEG_QUALITY), 90]), ''


@log
def save_image(image_data, image_save_format, target_folder, file_name_base, report_on_failure=False):
    """
    Saves an image to disk.

    Image is pushed to a queue polled by a worker thread

    :param image_data: the image data
    :type image_data: numpy.Array

    :param image_save_format: image file format specifier
    :type image_save_format: str

    :param target_folder: path to target folder
    :type target_folder: str

    :param file_name_base: filename base (without extension)
    :type file_name_base: str

    :param report_on_failure: ask worker thread to report save failure
    :type report_on_failure: bool
    """
    target_path = target_folder + "/" + file_name_base + '.' + image_save_format

    _IMAGE_SAVE_QUEUE.put({'image': image_data.copy(),
                           'target_path': target_path,
                           'report_on_failure': report_on_failure})


def _set_color_axis_as(wanted_axis, image_data):

    if image_data.ndim < 3:
        return image_data

    else:
        # find what axis are the colors on.
        # axis 0-based index is the index of the smallest data.shape item
        shape = image_data.shape
        color_axis = shape.index(min(shape))

        _LOGGER.debug(f"data color axis = {color_axis}. Wanted color axis = {wanted_axis}")

        if color_axis != wanted_axis:
            return numpy.moveaxis(image_data, color_axis, wanted_axis)

        return image_data
