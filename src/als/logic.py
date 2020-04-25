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
from typing import List

import als.model.data
from als import config
from als.code_utilities import log, AlsException, SignalingQueue
from als.crunching import compute_histograms_for_display
from als.io.input import InputScanner, ScannerStartError
from als.io.network import get_ip, WebServer
from als.io.output import ImageSaver
from als.model.base import Image, Session
from als.model.data import STACKING_MODE_MEAN, DYNAMIC_DATA, WORKER_STATUS_BUSY, WORKER_STATUS_IDLE
from als.model.params import ProcessingParameter
from als.processing import Pipeline, Debayer, Standardize, ConvertForOutput, Levels, ColorBalance, AutoStretch, RemoveDark
from als.stack import Stacker

gettext.install('als', 'locale')

_LOGGER = logging.getLogger(__name__)


class SessionError(AlsException):
    """
    Class for all errors related to session management
    """


class CriticalFolderMissing(SessionError):
    """Raised when a critical folder is missing"""


class WebServerStartFailure(AlsException):
    """Raised when web server fails"""


# pylint: disable=R0902, R0904
class Controller:
    """
    The application controller, in charge of implementing application logic
    """

    _BIN_COUNT = 512

    @log
    def __init__(self):

        DYNAMIC_DATA.session.set_status(Session.stopped)
        DYNAMIC_DATA.web_server_is_running = False
        self._save_every_image = False

        DYNAMIC_DATA.pre_processor_status = WORKER_STATUS_IDLE
        DYNAMIC_DATA.stacker_status = WORKER_STATUS_IDLE
        DYNAMIC_DATA.post_processor_status = WORKER_STATUS_IDLE
        DYNAMIC_DATA.saver_status = WORKER_STATUS_IDLE

        self._input_scanner: InputScanner = InputScanner.create_scanner()

        self._pre_process_queue: SignalingQueue = DYNAMIC_DATA.pre_process_queue
        self._pre_process_pipeline: Pipeline = Pipeline(
            'pre-process',
            self._pre_process_queue,
            [RemoveDark(), Debayer(), Standardize()])
        self._pre_process_pipeline.start()

        self._stacker_queue: SignalingQueue = DYNAMIC_DATA.stacker_queue
        self._stacker: Stacker = Stacker(self._stacker_queue)
        self._stacker.stacking_mode = STACKING_MODE_MEAN
        self._stacker.align_before_stack = True
        self._stacker.start()

        self._post_process_queue = DYNAMIC_DATA.process_queue
        self._post_process_pipeline: Pipeline = Pipeline('post-process', self._post_process_queue, [ConvertForOutput()])
        self._rgb_processor = ColorBalance()
        self._autostretch_processor = AutoStretch()
        self._levels_processor = Levels()
        self._post_process_pipeline.add_process(self._autostretch_processor)
        self._post_process_pipeline.add_process(self._levels_processor)
        self._post_process_pipeline.add_process(self._rgb_processor)
        self._post_process_pipeline.start()

        self._saver_queue = DYNAMIC_DATA.save_queue
        self._saver = ImageSaver(self._saver_queue)
        self._saver.start()

        self._last_stacking_result = None
        self._web_server = None

        self._model_observers = list()

        self._input_scanner.new_image_signal[Image].connect(self.on_new_image_read)
        self._pre_process_pipeline.new_result_signal[Image].connect(self.on_new_pre_processed_image)
        self._stacker.stack_size_changed_signal[int].connect(self.on_stack_size_changed)
        self._stacker.new_result_signal[Image].connect(self.on_new_stack_result)
        self._post_process_pipeline.new_result_signal[Image].connect(self.on_new_post_processor_result)

        self._pre_process_queue.size_changed_signal[int].connect(self.on_pre_process_queue_size_changed)
        self._stacker_queue.size_changed_signal[int].connect(self.on_stacker_queue_size_changed)
        self._post_process_queue.size_changed_signal[int].connect(self.on_post_processor_queue_size_changed)
        self._saver_queue.size_changed_signal[int].connect(self.on_saver_queue_size_changed)

        self._pre_process_pipeline.busy_signal.connect(self.on_pre_processor_busy)
        self._pre_process_pipeline.waiting_signal.connect(self.on_pre_processor_waiting)
        self._stacker.busy_signal.connect(self.on_stacker_busy)
        self._stacker.waiting_signal.connect(self.on_stacker_waiting)
        self._post_process_pipeline.busy_signal.connect(self.on_post_processor_busy)
        self._post_process_pipeline.waiting_signal.connect(self.on_post_processor_waiting)
        self._saver.busy_signal.connect(self.on_saver_busy)
        self._saver.waiting_signal.connect(self.on_saver_waiting)

        DYNAMIC_DATA.session.status_changed_signal.connect(self._notify_model_observers)

    @log
    def get_autostretch_parameters(self) -> List[ProcessingParameter]:
        """
        Retrieves autostretch parameters

        :return: autostretch parameters
        """
        return self._autostretch_processor.get_parameters()

    @log
    def get_rgb_parameters(self) -> List[ProcessingParameter]:
        """
        Retrieves rgb parameters

        :return: rgb parameters
        """
        return self._rgb_processor.get_parameters()

    @log
    def get_levels_parameters(self) -> List[ProcessingParameter]:
        """
        Retrieves Levels processor parameters

        :return: Levels processor parameters
        """
        return self._levels_processor.get_parameters()

    @log
    def remove_model_observer(self, observer):
        """
        Removes observer from our observers list.

        :param observer: the observer to remove
        :type observer: any
        """
        if observer in self._model_observers:
            self._model_observers.remove(observer)

    @log
    def _notify_model_observers(self, image_only=False):
        """
        Tells all registered observers to update their display
        """
        for observer in self._model_observers:
            observer.update_display(image_only)

    @log
    def add_model_observer(self, observer):
        """
        Adds an observer to our observers list.

        :param observer: the new observer
        :type observer: any
        """
        self._model_observers.append(observer)

    @log
    def apply_processing(self):
        """
        Apply processing on last stacking result
        """
        if self._stacker.size > 0 and DYNAMIC_DATA.process_queue.qsize() == 0:

            DYNAMIC_DATA.process_queue.put(self._last_stacking_result.clone())

    @log
    def get_save_every_image(self) -> bool:
        """
        Retrieves the flag that tells if we need to save every process result image

        :return: the flag that tells if we need to save every process result image
        :rtype: bool
        """
        return self._save_every_image

    @log
    def set_save_every_image(self, save_every_image: bool):
        """
        Sets the flag that tells if we need to save every process result image

        :param save_every_image: flag that tells if we need to save every process result image
        :type save_every_image: bool
        """
        self._save_every_image = save_every_image

    @log
    def get_align_before_stack(self) -> bool:
        """
        Gets "align before stack" switch

        :return: Do we align before stacking ?
        :rtype: bool
        """
        return self._stacker.align_before_stack

    @log
    def set_align_before_stack(self, align: bool):
        """
        Sets "align before stack" switch

        :param align: Do we align before stacking ?
        :type align: bool
        """
        self._stacker.align_before_stack = align

    @log
    def get_stacking_mode(self):
        """
        Gets current stacking mode

        :return: the stacking mode
        :rtype: str
        """
        return self._stacker.stacking_mode

    @log
    def set_stacking_mode(self, mode):
        """
        Sets current stacking mode

        :param mode: stacking mode
        :type mode: str
        """
        self._stacker.stacking_mode = mode

    @log
    def on_stack_size_changed(self, size):
        """
        Stack size just changed

        :param size: the stack size
        :type size: int
        """
        DYNAMIC_DATA.stack_size = size
        self._notify_model_observers()

    @log
    def on_new_post_processor_result(self, image: Image):
        """
        A new image processing result is here

        :param image: the new processing result
        :type image: Image
        """
        image.origin = "Process result"
        DYNAMIC_DATA.histogram_container = compute_histograms_for_display(image, Controller._BIN_COUNT)
        DYNAMIC_DATA.post_processor_result = image
        self._notify_model_observers(image_only=True)
        self.save_post_process_result()

    @log
    def on_new_stack_result(self, image: Image):
        """
        A new image has been stacked

        :param image: the result of the stack
        :type image: Image
        """
        image.origin = "Stacking result"
        self._last_stacking_result = image.clone()

        self.purge_queue(self._post_process_queue)
        self._post_process_queue.put(image.clone())

    @log
    def on_new_image_read(self, image: Image):
        """
        A new image as been read by input scanner

        :param image: the new image
        :type image: Image
        """
        self._pre_process_queue.put(image)

    @log
    def on_new_pre_processed_image(self, image: Image):
        """
        A new image as been pre-processed

        :param image: the image
        :type image: Image
        """
        self._stacker_queue.put(image)

    @log
    def on_pre_process_queue_size_changed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the pre-processor queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New pre-processor queue size : {new_size}")
        self._notify_model_observers()

    @log
    def on_stacker_queue_size_changed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the stacker queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New stacker queue size : {new_size}")
        self._notify_model_observers()

    @log
    def on_post_processor_queue_size_changed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the process queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New post-processor queue size : {new_size}")
        self._notify_model_observers()

    @log
    def on_saver_queue_size_changed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the save queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New saver queue size : {new_size}")
        self._notify_model_observers()

    @log
    def on_pre_processor_busy(self):
        """
        pre-processor just started working on new image
        """
        DYNAMIC_DATA.pre_processor_status = WORKER_STATUS_BUSY
        self._notify_model_observers()

    @log
    def on_pre_processor_waiting(self):
        """
        pre-processor just finished working on new image
        """
        DYNAMIC_DATA.pre_processor_status = WORKER_STATUS_IDLE
        self._notify_model_observers()

    @log
    def on_stacker_busy(self):
        """
        stacker just started working on new image
        """
        DYNAMIC_DATA.stacker_status = WORKER_STATUS_BUSY
        self._notify_model_observers()

    @log
    def on_stacker_waiting(self):
        """
        stacker just finished working on new image
        """
        DYNAMIC_DATA.stacker_status = WORKER_STATUS_IDLE
        self._notify_model_observers()

    @log
    def on_post_processor_busy(self):
        """
        post-processor just started working on new image
        """
        DYNAMIC_DATA.post_processor_status = WORKER_STATUS_BUSY
        self._notify_model_observers()

    @log
    def on_post_processor_waiting(self):
        """
        post-processor just finished working on new image
        """
        DYNAMIC_DATA.post_processor_status = WORKER_STATUS_IDLE
        self._notify_model_observers()

    @log
    def on_saver_busy(self):
        """
        saver just started working on new image
        """
        DYNAMIC_DATA.saver_status = WORKER_STATUS_BUSY
        self._notify_model_observers()

    @log
    def on_saver_waiting(self):
        """
        saver just finished working on new image
        """
        DYNAMIC_DATA.saver_status = WORKER_STATUS_IDLE
        self._notify_model_observers()

    @log
    def start_session(self):
        """
        Starts session
        """
        try:
            if DYNAMIC_DATA.session.is_stopped:

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
                        raise CriticalFolderMissing(title, message)

            else:
                # session was paused when this start was ordered. No need for checks & setup
                _LOGGER.info("Restarting input scanner ...")

            # start input scanner
            try:
                self._input_scanner.start()
                _LOGGER.info("Input scanner started")
            except ScannerStartError as scanner_start_error:
                raise SessionError("Input scanner could not start", scanner_start_error)

            running_mode = f"{self._stacker.stacking_mode}"
            running_mode += " with alignment" if self._stacker.align_before_stack else " without alignment"
            _LOGGER.info(f"Session running in mode {running_mode}")
            DYNAMIC_DATA.session.set_status(Session.running)

        except SessionError as session_error:
            _LOGGER.error(f"Session error. {session_error.message} : {session_error.details}")
            raise

    @log
    def stop_session(self):
        """
        Stops session : stop input scanner and purge input queue
        """
        if not DYNAMIC_DATA.session.is_stopped:
            self._stop_input_scanner()
            Controller.purge_queue(self._pre_process_queue)
            Controller.purge_queue(self._stacker_queue)
            Controller.purge_queue(self._post_process_queue)
            _LOGGER.info("Session stopped")
            DYNAMIC_DATA.session.set_status(Session.stopped)

    @log
    def pause_session(self):
        """
        Pauses session : just stop input scanner
        """
        if DYNAMIC_DATA.session.is_running:
            self._stop_input_scanner()
        _LOGGER.info("Session paused")
        DYNAMIC_DATA.session.set_status(Session.paused)

    @log
    def start_www(self):
        """Starts web server"""

        work_folder = config.get_work_folder_path()
        ip_address = get_ip()
        port_number = config.get_www_server_port_number()

        # setup work folder
        try:
            Controller._setup_web_content()
        except OSError as os_error:
            raise WebServerStartFailure("Work folder could not be prepared", str(os_error))

        try:
            self._web_server = WebServer(work_folder)
            self._web_server.start()

            if ip_address == "127.0.0.1":
                log_function = _LOGGER.warning
            else:
                log_function = _LOGGER.info

            url = f"http://{ip_address}:{port_number}"
            log_function(f"Web server started. Reachable at {url}")

            DYNAMIC_DATA.web_server_ip = ip_address
            DYNAMIC_DATA.web_server_is_running = True
            self._notify_model_observers()

        except OSError as os_error:
            title = "Could not start web server"
            _LOGGER.error(f"{title} : {os_error}")
            raise WebServerStartFailure(title, str(os_error))

    @log
    def stop_www(self):
        """Stops web server"""

        if self._web_server and DYNAMIC_DATA.web_server_is_running:
            self._web_server.stop()
            self._web_server.join()
            self._web_server = None
            _LOGGER.info("Web server stopped")
            DYNAMIC_DATA.web_server_is_running = False
            self._notify_model_observers()

    @staticmethod
    @log
    def purge_queue(queue: SignalingQueue):
        """
        Purge a queue

        :param queue: the queue to purge
        :type queue: SignalingQueue
        """

        while not queue.empty():
            queue.get()

    @staticmethod
    @log
    def _setup_web_content():
        """Prepares the work folder."""

        work_dir_path = config.get_work_folder_path()
        resources_dir_path = str(Path(os.path.dirname(os.path.realpath(__file__))).parent/"resources")

        with open(resources_dir_path + "/index.html", 'r') as file:
            index_content = file.read()

        index_content = index_content.replace('##PERIOD##', str(config.get_www_server_refresh_period()))

        with open(work_dir_path + "/index.html", 'w') as file:
            file.write(index_content)

        standby_image_path = work_dir_path + "/" + als.model.data.WEB_SERVED_IMAGE_FILE_NAME_BASE
        standby_image_path += '.' + als.model.data.IMAGE_SAVE_TYPE_JPEG
        shutil.copy(resources_dir_path + "/waiting.jpg", standby_image_path)

    @log
    def save_post_process_result(self):
        """
        Saves stacking result image to disk
        """

        # we save the image no matter what, then save a jpg for the web server if it is running
        image = DYNAMIC_DATA.post_processor_result

        self.save_image(image,
                        config.get_image_save_format(),
                        config.get_work_folder_path(),
                        als.model.data.STACKED_IMAGE_FILE_NAME_BASE)

        if DYNAMIC_DATA.web_server_is_running:
            self.save_image(image,
                            als.model.data.IMAGE_SAVE_TYPE_JPEG,
                            config.get_work_folder_path(),
                            als.model.data.WEB_SERVED_IMAGE_FILE_NAME_BASE)

        # if user want to save every image, we save a timestamped version
        if self._save_every_image:
            self.save_image(image,
                            config.get_image_save_format(),
                            config.get_work_folder_path(),
                            als.model.data.STACKED_IMAGE_FILE_NAME_BASE,
                            add_timestamp=True)

    # pylint: disable=R0913
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
        self._saver_queue.put(image_to_save)

    @log
    def shutdown(self):
        """
        Proper shutdown of all app components
        """
        if not DYNAMIC_DATA.session.is_stopped:
            self.stop_session()

        if DYNAMIC_DATA.web_server_is_running:
            self.stop_www()

        self._pre_process_pipeline.stop()
        self._stacker.stop()
        self._post_process_pipeline.stop()

        self._saver.stop()
        self._saver.wait()

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
