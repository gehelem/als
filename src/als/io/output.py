"""
Everything we need to perform outputs from ALS

For now, we only save some images to disk, but who knows...
"""
import logging
import os
import sys
from pathlib import Path

import cv2
from PyQt5.QtCore import QT_TRANSLATE_NOOP

import als.model.data
from als.code_utilities import log, SignalingQueue
from als.messaging import MESSAGE_HUB
from als.model.base import Image
from als.processing import QueueConsumer

_LOGGER = logging.getLogger(__name__)


class ImageSaver(QueueConsumer):
    """
    Saves images according to commands posted to IMAGE_SAVE_QUEUE in its own thread

    """
    @log
    def __init__(self, save_queue: SignalingQueue):
        QueueConsumer.__init__(self, "save", save_queue)

    @log
    def _handle_image(self, image: Image):

        ImageSaver._save_image(image)

    @staticmethod
    @log
    def _save_image(image):
        """
        Saves image to disk

        :param image: the image to save
        :type image: Image
        """
        target_path = image.destination
        cwd = os.getcwd()

        if sys.platform == 'win32':
            os.chdir(Path(target_path).parent)
            target_path = Path(target_path).name

        if target_path.endswith('.' + als.model.data.IMAGE_SAVE_TYPE_TIFF):
            save_is_successful, failure_details = ImageSaver._save_image_as_tiff(image, target_path)

        elif target_path.endswith('.' + als.model.data.IMAGE_SAVE_TYPE_PNG):
            save_is_successful, failure_details = ImageSaver._save_image_as_png(image, target_path)

        elif target_path.endswith('.' + als.model.data.IMAGE_SAVE_TYPE_JPEG):
            save_is_successful, failure_details = ImageSaver._save_image_as_jpg(image, target_path)

        else:
            # Unsupported format in config file. Should never happen
            save_is_successful, failure_details = False, f"Unsupported File format for {target_path}"

        if save_is_successful:
            MESSAGE_HUB.dispatch_info(
                __name__,
                QT_TRANSLATE_NOOP("", "Image saved : {}"),
                [
                    ((os.getcwd() + os.sep) if sys.platform == 'win32' else "") + target_path,
                ]
            )

        else:
            details = target_path

            if failure_details.strip():
                details += ' : ' + failure_details

            MESSAGE_HUB.dispatch_error(__name__, QT_TRANSLATE_NOOP("", "Failed to save image : {}"), [details, ])

        if sys.platform == 'win32':
            os.chdir(cwd)

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
        cv2_color_conversion_flag = cv2.COLOR_RGB2BGR if image.is_color() else cv2.COLOR_GRAY2BGR
        return cv2.imwrite(target_path, cv2.cvtColor(image.data, cv2_color_conversion_flag)), ""

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
        cv2_color_conversion_flag = cv2.COLOR_RGB2BGR if image.is_color() else cv2.COLOR_GRAY2BGR
        return cv2.imwrite(target_path,
                           cv2.cvtColor(image.data, cv2_color_conversion_flag),
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
        # here we are sure that image data type is unsigned 16 bits. We need to downscale to 8 bits
        image.data = (image.data / (((2 ** 16) - 1) / ((2 ** 8) - 1))).astype('uint8')
        cv2_color_conversion_flag = cv2.COLOR_RGB2BGR if image.is_color() else cv2.COLOR_GRAY2BGR

        return cv2.imwrite(target_path,
                           cv2.cvtColor(image.data, cv2_color_conversion_flag),
                           [int(cv2.IMWRITE_JPEG_QUALITY), 90]), ''
