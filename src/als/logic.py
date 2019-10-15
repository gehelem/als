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
from pathlib import Path

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QDialog

from als import config
from als.code_utilities import log
from als.io.input import InputScanner, ScannerStartError
from als.model import DYNAMIC_DATA, Image, SignalingQueue, Session
from als.processing import PreProcessPipeline
from als.stack import Stacker
from als.ui.dialogs import question, PreferencesDialog

gettext.install('als', 'locale')

_LOGGER = logging.getLogger(__name__)


class SessionManagementError(Exception):
    """
    Base class for all errors related to session management
    """
    def __init__(self, message, error):
        Exception.__init__(self)
        self.message = message
        self.error = error


class Controller(QObject):
    """
    The application controller, in charge of implementing application logic
    """
    @log
    def __init__(self):
        QObject.__init__(self)
        DYNAMIC_DATA.session.set_status(Session.stopped)
        DYNAMIC_DATA.web_server_is_running = False

        self._input_scanner: InputScanner = InputScanner.create_scanner(DYNAMIC_DATA.input_queue)
        self._input_queue: SignalingQueue = DYNAMIC_DATA.input_queue

        self._pre_process_pipeline = PreProcessPipeline(DYNAMIC_DATA.input_queue)
        self._pre_process_pipeline.start()

        self._stacker = Stacker(DYNAMIC_DATA.stack_queue, DYNAMIC_DATA.process_queue)
        self._stacker_queue = DYNAMIC_DATA.stack_queue
        self._stacker.start()

        self._input_scanner.new_image_signal[Image].connect(self.on_new_image_read)
        self._pre_process_pipeline.new_result_signal[Image].connect(self.on_new_pre_processed_image)
        self._stacker.stack_size_changed_signal[int].connect(DYNAMIC_DATA.set_stack_size)

    @log
    def on_new_image_read(self, image: Image):
        """
        A new image as been read by input scanner

        :param image: the new image
        :type image: Image
        """
        self._input_queue.put(image)

    @log
    def on_new_pre_processed_image(self, image: Image):
        """
        A new image as been pre-processed

        :param image: the image
        :type image: Image
        """
        self._stacker_queue.put(image)

    @log
    def start_session(self):
        """
        Starts session
        """
        try:
            if DYNAMIC_DATA.session.is_stopped():

                _LOGGER.info("Starting new session...")

                self._stacker.reset()

                folders_dict = {
                    "scan": config.get_scan_folder_path(),
                    "work": config.get_work_folder_path()
                }

                # checking presence of both scan & work folders
                for role, path in folders_dict.items():
                    if not Path(path).is_dir():
                        title = "Missing critical folder"
                        message = f"Your currently configured {role} folder '{path}' is missing."
                        folder_now_exists = False
                        if question(title, message + "Do you want to review your preferences ?"):
                            dialog = PreferencesDialog(QApplication.activeWindow())
                            # if prefs dialog is closed by "OK", a.k.a. Accepted, we are sure that folder now exists,
                            # as it has been selected with OS folder selector.
                            folder_now_exists = dialog.exec() == QDialog.Accepted
                        if not folder_now_exists:
                            raise SessionManagementError(title, message)

                # setup work folder
                try:
                    self.setup_work_folder()
                except OSError as os_error:
                    raise SessionManagementError("Work folder could not be prepared", os_error)

            else:
                _LOGGER.info("Restarting input scanner ...")

            # start input scanner
            try:
                self._input_scanner.start()
                _LOGGER.info("Input scanner started")
            except ScannerStartError as scanner_start_error:
                raise SessionManagementError("Input scanner could not start", scanner_start_error)

            running_mode = f"{DYNAMIC_DATA.stacking_mode}"
            running_mode += " with alignment" if DYNAMIC_DATA.align_before_stacking else " without alignment"
            _LOGGER.info(f"Session running in mode {running_mode}")
            DYNAMIC_DATA.session.set_status(Session.running)

        except SessionManagementError as session_error:
            _LOGGER.error(f"Session error. {session_error.message} : {session_error.error}")
            raise

    @log
    def stop_session(self, ask_confirmation: bool = True):
        """
        Stops session : stop input scanner and purge input queue

        :param ask_confirmation: Do we ask for user confirmation
        :type ask_confirmation: bool
        """

        title = "Really stop session ?"
        message = """Stopping the current session will reset the stack and all image enhancements.
        
        Are you sure you want to stop the current session ?
        """
        do_stop_session = True if not ask_confirmation else question(title, message)

        if do_stop_session:
            if DYNAMIC_DATA.session.is_running():
                self._stop_input_scanner()
            self.purge_input_queue()
            _LOGGER.info("Session stopped")
            DYNAMIC_DATA.session.set_status(Session.stopped)

    @log
    def pause_session(self):
        """
        Pauses session : just sop input scanner
        """
        if DYNAMIC_DATA.session.is_running():
            self._stop_input_scanner()
        _LOGGER.info("Session paused")
        DYNAMIC_DATA.session.set_status(Session.paused)

    @log
    def purge_input_queue(self):
        """
        Purge the input queue

        """
        while not DYNAMIC_DATA.input_queue.empty():
            DYNAMIC_DATA.input_queue.get()
        _LOGGER.info("Input queue purged")

    @log
    def purge_stack_queue(self):
        """
        Purge the stack queue

        """
        while not DYNAMIC_DATA.stack_queue.empty():
            DYNAMIC_DATA.stack_queue.get()
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
        image = DYNAMIC_DATA.process_result

        self.save_image(image,
                        config.get_image_save_format(),
                        config.get_work_folder_path(),
                        config.STACKED_IMAGE_FILE_NAME_BASE)

        if DYNAMIC_DATA.web_server_is_running:
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
        Save an image to disk.

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
        DYNAMIC_DATA.save_queue.put(image_to_save)

    @log
    def shutdown(self):
        """
        Proper shutdown of all app components
        """
        if not DYNAMIC_DATA.session.is_stopped():
            self.stop_session(ask_confirmation=False)

        self._pre_process_pipeline.stop()
        self._stacker.stop()

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

    @log
    def _stop_input_scanner(self):
        self._input_scanner.stop()
        _LOGGER.info("Input scanner stopped")
