# !/usr/bin/python3
# -*- coding: utf-8 -*-

# ALS - Astro Live Stacker
# Copyright (C) 2019  Sébastien Durand (Dragonlost) - Gilles Le Maréchal (Gehelem)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Module holding all application logic
"""
import gettext
import logging
import os
import shutil
from datetime import datetime

from PyQt5.QtCore import QObject
from als import config
from als.code_utilities import log
from als.model import STORE, Image

gettext.install('als', 'locale')

_LOGGER = logging.getLogger(__name__)


class Controller(QObject):
    """
    The application controller, in charge of implementing application logic
    """
    @log
    def purge_input_queue(self):
        """
        Purge the input queue

        """
        while not STORE.input_queue.empty():
            STORE.input_queue.get()
        _LOGGER.info("Input queue purged")

    @log
    def purge_stack_queue(self):
        """
        Purge the stack queue

        """
        while not STORE.stack_queue.empty():
            STORE.stack_queue.get()
        _LOGGER.info("Stack queue purged")

    @log
    def setup_work_folder(self):
        """Prepares the work folder."""

        work_dir_path = config.get_work_folder_path()
        resources_dir_path = os.path.dirname(os.path.realpath(__file__)) + "/../resources"

        shutil.copy(resources_dir_path + "/index.html", work_dir_path)

        standby_image_path = work_dir_path + "/" + config.WEB_SERVED_IMAGE_FILE_NAME_BASE + '.' + config.IMAGE_SAVE_JPEG
        shutil.copy(resources_dir_path + "/waiting.jpg", standby_image_path)

    @log
    def save_process_result(self):
        """
        Saves stacking result image to disk
        """

        # we save the image no matter what, then save a jpg for the webserver if it is running
        image = STORE.process_result

        self.save_image(image,
                        config.get_image_save_format(),
                        config.get_work_folder_path(),
                        config.STACKED_IMAGE_FILE_NAME_BASE)

        if STORE.web_server_is_running:
            self.save_image(image,
                            config.IMAGE_SAVE_JPEG,
                            config.get_work_folder_path(),
                            config.WEB_SERVED_IMAGE_FILE_NAME_BASE)

    @log
    def save_image(self, image: Image,
                   file_extension: str,
                   dest_folder_path: str,
                   filename_base: str,
                   add_timestamp: bool = False):
        """
        Save an image to disk
        :param image: the image to save
        :type image: Image
        :param file_extension: The image save file format extension
        :type file_extension: str
        :param dest_folder_path: The path of the folder image will be saved to
        :type dest_folder_path: str
        :param filename_base: The name of the file to save to (without extension)
        :type filename_base: str
        :param add_timestamp: Do we add a timestamp to image name
        :type add_timestamp: bool
        """
        filename_base = filename_base

        if add_timestamp:
            filename_base += '-' + Controller.get_timestamp()

        image_to_save = image.clone()
        image_to_save.destination = dest_folder_path + "/" + filename_base + '.' + file_extension
        STORE.save_queue.put(image_to_save)

    @staticmethod
    @log
    def get_timestamp():
        """
        Return a timestamp build from current date and time

        :return: the timestamp
        :rtype: str
        """
        timestamp = str(datetime.fromtimestamp(datetime.timestamp(datetime.now())))
        timestamp = timestamp.replace(' ', "-").replace(":", '-').replace('.', '-')
        return timestamp
