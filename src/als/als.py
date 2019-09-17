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
"""The main module for ALS.

Needs refactoring : too many unrelated classes"""
import gettext
import logging
import os
import shutil
import sys
import threading
from datetime import datetime
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler

import cv2
import numpy as np
from PyQt5.QtCore import pyqtSignal, QFileInfo, QThread, Qt, pyqtSlot, QTimer, QEvent
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication

from astroalign import MaxIterError
from qimage2ndarray import array2qimage
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from als import preprocess as prepro, stack as stk, model
from als.code_utilities import log
from als.io.output import ImageSaver, save_image
from als.model import VERSION, STORE
from als.ui.dialogs import PreferencesDialog, question, error_box, warning_box, AboutDialog

try:
    from als import config
except ValueError as value_error:
    error_box("Config file is invalid", str(value_error))
    print(f"***** ERROR : user config file is invalid : {value_error}")
    sys.exit(1)

from generated.als_ui import Ui_stack_window

DEFAULT_SCAN_SIZE_RETRY_PERIOD_MS = 100
LOG_DOCK_INITIAL_HEIGHT = 60

gettext.install('als', 'locale')

_LOGGER = logging.getLogger(__name__)


class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""
    @log
    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath


class HTTPServer(BaseHTTPServer):
    """The main server, you pass in base_path which is the path you want to serve requests from"""
    @log
    def __init__(self, base_path, server_address, request_handler_class=HTTPHandler):
        self.base_path = base_path
        BaseHTTPServer.__init__(self, server_address, request_handler_class)


class StoppableServerThread(threading.Thread):
    """
    Thread class with a stop() method.

    The thread itself has to check regularly for the stopped() condition.
    """

    # FIXME logging this init causes issue with server thread init. To be investigated
    #  @log
    def __init__(self, web_dir):
        # web stuff
        self.web_dir = web_dir
        self.httpd = HTTPServer(self.web_dir, ("", config.get_www_server_port_number()))
        self.httpd.timeout = 1

        # thread stuff
        self._stop_event = threading.Event()

        # Init parent thread
        super().__init__(target=self.serve)

    @log
    def serve(self):
        """
        Continuously handles incomming HTTP requests.
        """
        while not self.stopped():
            self.httpd.handle_request()

    @log
    def stop(self):
        """
        Stops the web server.
        """
        self._stop_event.set()

    def stopped(self):
        """
        Checks if server is stopped.

        :return: True if server is stopped, False otherwise
        """
        return self._stop_event.is_set()


class ImageRefSave:
    """TODO"""

    # pylint: disable=R0903
    @log
    def __init__(self):
        self.image = None
        self.status = "stop"
        self.stack_image = None


class MyEventHandler(FileSystemEventHandler, QThread, ImageRefSave):
    """Filesystem event handler used to detect new images in a folder."""
    created_signal = pyqtSignal(str)

    @log
    def __init__(self):
        super().__init__()

    @log
    def on_moved(self, event):
        if event.event_type == 'moved':
            image_path = event.dest_path
            _LOGGER.info(f"New image ready to be processed : {image_path}")
            _LOGGER.debug(f"'created' signal emitted from MyEventHandler.on_moved. Image path = {image_path}")
            self.created_signal.emit(image_path)

    @log
    def on_created(self, event):
        if event.event_type == 'created':
            file_is_incomplete = True
            last_file_size = -1
            image_path = event.src_path
            _LOGGER.debug(f"New image file detected : {image_path}. Waiting untill file is fully written to disk...")

            while file_is_incomplete:
                info = QFileInfo(image_path)
                size = info.size()
                _LOGGER.debug(f"File {image_path}'s size = {size}")
                if size == last_file_size:
                    file_is_incomplete = False
                    _LOGGER.debug(f"File {image_path} has been fully written to disk")
                last_file_size = size
                self.msleep(DEFAULT_SCAN_SIZE_RETRY_PERIOD_MS)

            _LOGGER.info(f"New image ready to be processed : {image_path}")
            _LOGGER.debug(f"'created' signal emitted from MyEventHandler.on_created. Image path = {image_path}")
            self.created_signal.emit(image_path)


# ------------------------------------------------------------------------------


class WatchOutForFileCreations(QThread):
    """This object listens to filesystem events and triggers image read and processing.

    Needs refactoring : It does too much things and should not be given GUI state"""
    print_image = pyqtSignal()

    @log
    def __init__(self, path, work_folder, align_on, save_on, stack_method,
                 log_ui, white_slider, black_slider, contrast_slider, brightness_slider,
                 r_slider, g_slider, b_slider, apply_button,
                 image_ref_save,
                 scnr_on, scnr_mode, scnr_value,
                 wavelets_on, wavelets_type, wavelets_use_luminance,
                 wavelet_1_value, wavelet_2_value, wavelet_3_value,
                 wavelet_4_value, wavelet_5_value):

        super().__init__()
        self.align_on = align_on
        self.save_on = save_on
        self.stack_method = stack_method
        self.white_slider = white_slider
        self.black_slider = black_slider
        self.contrast_slider = contrast_slider
        self.brightness_slider = brightness_slider
        self.r_slider = r_slider
        self.g_slider = g_slider
        self.b_slider = b_slider
        self.apply_button = apply_button
        self.log = log_ui
        self.path = path
        self.work_folder = work_folder
        self.first = 0
        self.counter = 0
        self.first_image = None
        self.image_ref_save = image_ref_save
        self.ref_image = None
        self.scnr_on = scnr_on
        self.scnr_mode = scnr_mode
        self.scnr_value = scnr_value
        self.wavelets_on = wavelets_on
        self.wavelets_type = wavelets_type
        self.wavelets_use_luminance = wavelets_use_luminance
        self.wavelet_1_value = wavelet_1_value
        self.wavelet_2_value = wavelet_2_value
        self.wavelet_3_value = wavelet_3_value
        self.wavelet_4_value = wavelet_4_value
        self.wavelet_5_value = wavelet_5_value
        _LOGGER.info(f" Work folder = '{self.work_folder}'")
        _LOGGER.info(f" Scan folder = '{self.path}'")

        # __ call watchdog __
        # call observer :
        self.observer = Observer()
        # call observer class :
        self.event_handler = MyEventHandler()
        self.observer.schedule(self.event_handler, self.path, recursive=False)
        self.observer.start()

        self.event_handler.created_signal[str].connect(self.created)

    @log
    def created(self, new_image_path):
        """
        trigger image stacking.

        :param new_image_path: path to image file to stack
        :type new_image_path: str
        :return: None
        """

        new_image_file_name = new_image_path.split("/")[-1]
        ignored_start_patterns = ['.', '~', 'tmp']
        to_be_ignored = False

        for pattern in ignored_start_patterns:
            if new_image_file_name.startswith(pattern):
                to_be_ignored = True
                break

        if self.image_ref_save.status == "play" and not to_be_ignored:

            self.counter = self.counter + 1
            self.log.append(_("Reading new frame..."))
            if self.first == 0:
                self.log.append(_("Reading first frame..."))
                self.first_image, limit, mode = stk.create_first_ref_im(self.work_folder, new_image_path,
                                                                        save_im=self.save_on)

                self.image_ref_save.image = self.first_image

                self.image_ref_save.stack_image = prepro.post_process_image(self.image_ref_save.image,
                                                                            self.log,
                                                                            mode=mode, scnr_on=self.scnr_on.isChecked(),
                                                                            wavelets_on=self.wavelets_on.isChecked(),
                                                                            wavelets_type=str(self.wavelets_type.currentText()),
                                                                            wavelets_use_luminance=self.wavelets_use_luminance.isChecked(),
                                                                            param=[self.contrast_slider.value() / 10.,
                                                                                   self.brightness_slider.value(),
                                                                                   self.black_slider.value(),
                                                                                   self.white_slider.value(),
                                                                                   self.r_slider.value() / 100.,
                                                                                   self.g_slider.value() / 100.,
                                                                                   self.b_slider.value() / 100.,
                                                                                   self.scnr_mode.currentText(),
                                                                                   self.scnr_value.value(),
                                                                                   {1: int(self.wavelet_1_value.text()) / 100.,
                                                                                    2: int(self.wavelet_2_value.text()) / 100.,
                                                                                    3: int(self.wavelet_3_value.text()) / 100.,
                                                                                    4: int(self.wavelet_4_value.text()) / 100.,
                                                                                    5: int(self.wavelet_5_value.text()) / 100.}])
                self.first = 1
                self.white_slider.setMaximum(np.int(limit))
                self.brightness_slider.setMaximum(np.int(limit) / 2.)
                self.brightness_slider.setMinimum(np.int(-1 * limit) / 2.)
                if self.white_slider.value() > limit:
                    self.white_slider.setSliderPosition(limit)
                elif self.white_slider.value() < -1 * limit:
                    self.white_slider.setSliderPosition(-1 * limit)
                self.black_slider.setMaximum(np.int(limit))
                if self.black_slider.value() > limit:
                    self.black_slider.setSliderPosition(limit)
                if self.brightness_slider.value() > limit / 2.:
                    self.brightness_slider.setSliderPosition(limit / 2.)
                if limit == 2. ** 16 - 1:
                    self.log.append(_("Read 16bit frame ..."))
                elif limit == 2. ** 8 - 1:
                    self.log.append(_("Read 8bit frame ..."))
                if mode == "rgb":
                    self.r_slider.setEnabled(True)
                    self.g_slider.setEnabled(True)
                    self.b_slider.setEnabled(True)
                self.white_slider.setEnabled(True)
                self.black_slider.setEnabled(True)
                self.contrast_slider.setEnabled(True)
                self.brightness_slider.setEnabled(True)
                self.apply_button.setEnabled(True)

            else:
                # appel de la fonction stack live
                if self.align_on:
                    self.log.append(_("Stack and Align New frame..."))
                else:
                    self.log.append(_("Stack New frame..."))

                try:
                    self.image_ref_save.image, limit, mode = stk.stack_live(self.work_folder, new_image_path,
                                                                            self.counter,
                                                                            ref=self.image_ref_save.image,
                                                                            first_ref=self.first_image,
                                                                            save_im=self.save_on,
                                                                            align=self.align_on,
                                                                            stack_methode=self.stack_method)
                except MaxIterError:
                    message = _(f"WARNING : {new_image_path} could not be aligned : Max iteration reached. "
                                f"Image is ignored")
                    self.log.append(message)
                    _LOGGER.warning(message)
                    return

                self.image_ref_save.stack_image = prepro.post_process_image(self.image_ref_save.image,
                                                                            self.log,
                                                                            mode=mode, scnr_on=self.scnr_on.isChecked(),
                                                                            wavelets_on=self.wavelets_on.isChecked(),
                                                                            wavelets_type=str(self.wavelets_type.currentText()),
                                                                            wavelets_use_luminance=self.wavelets_use_luminance.isChecked(),
                                                                            param=[self.contrast_slider.value() / 10.,
                                                                                   self.brightness_slider.value(),
                                                                                   self.black_slider.value(),
                                                                                   self.white_slider.value(),
                                                                                   self.r_slider.value() / 100.,
                                                                                   self.g_slider.value() / 100.,
                                                                                   self.b_slider.value() / 100.,
                                                                                   self.scnr_mode.currentText(),
                                                                                   self.scnr_value.value(),
                                                                                   {1: int(self.wavelet_1_value.text()) / 100.,
                                                                                    2: int(self.wavelet_2_value.text()) / 100.,
                                                                                    3: int(self.wavelet_3_value.text()) / 100.,
                                                                                    4: int(self.wavelet_4_value.text()) / 100.,
                                                                                    5: int(self.wavelet_5_value.text()) / 100.}])

                self.log.append(_("... Stack finished"))

            save_stack_result(self.image_ref_save.stack_image)
            self.print_image.emit()
        else:
            message = _("New image detected but not considered")
            self.log.append(message)
            _LOGGER.info(message)


# ------------------------------------------------------------------------------


class MainWindow(QMainWindow):
    """ALS main window."""

    @log
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_stack_window()
        self._ui.setupUi(self)

        # store if docks must be shown or not
        self.shown_log_dock = True
        self.show_session_dock = True

        self.running = False
        self.counter = 0
        self.align = False
        self.pause = False
        self.image_ref_save = ImageRefSave()
        self._ui.postprocess_widget.setCurrentIndex(0)

        self.setWindowTitle(_("Astro Live Stacker") + f" - v{VERSION}")

        # web stuff
        self.thread = None
        self.web_dir = None

        # prevent log dock to be too tall
        self.resizeDocks([self._ui.log_dock], [LOG_DOCK_INITIAL_HEIGHT], Qt.Vertical)

        model.STORE.add_observer(self)
        model.STORE.scan_in_progress = False
        model.STORE.web_server_is_running = False

        self._image_saver = ImageSaver()
        self._image_saver.save_successful_signal[str].connect(self.on_image_save_success)
        self._image_saver.save_fail_signal[str].connect(self.on_image_save_failure)
        self._image_saver.start()

    @log
    def closeEvent(self, event):
        """Handles window close events."""
        # pylint: disable=C0103

        self._stop_www()

        _LOGGER.debug(f"Window size : {self.size()}")
        _LOGGER.debug(f"Window position : {self.pos()}")

        window_rect = self.geometry()
        config.set_window_geometry((window_rect.x(), window_rect.y(), window_rect.width(), window_rect.height()))
        config.save()

        self._image_saver.stop()

        if self._image_saver.isRunning():
            message = "Making sure all images are saved..."
            _LOGGER.info(message)
            self._ui.log.append(message)
            self._ui.statusBar.showMessage(message)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self._image_saver.wait()

        super().closeEvent(event)

    @log
    def changeEvent(self, event):
        """Handles window change events."""
        # pylint: disable=C0103

        event.accept()

        # if window is going out of minimized state, we restore docks if needed
        if event.type() == QEvent.WindowStateChange:
            if not self.windowState() & Qt.WindowMinimized:
                _LOGGER.debug("Restoring docks visibility")
                if self.shown_log_dock:
                    self._ui.log_dock.show()
                if self.show_session_dock:
                    self._ui.session_dock.show()

    @log
    def resizeEvent(self, event):
        """Handles window resize events."""
        # pylint: disable=C0103

        super().resizeEvent(event)
        self.update_image(False)

    # ------------------------------------------------------------------------------
    # Callbacks

    @pyqtSlot(int, name="on_SCNR_Slider_valueChanged")
    @log
    def cb_scnr_slider_changed(self, value):
        """
        Qt slot for SCNR slider changes.

        :param value: SCNR slider new value
        :type value: int
        """
        self._ui.SCNR_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_R_slider_valueChanged")
    @log
    def cb_r_slider_changed(self, value):
        """
        Qt slot for R slider changes.

        :param value: R slider new value
        :type value: int
        """
        self._ui.R_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_G_slider_valueChanged")
    @log
    def cb_g_slider_changed(self, value):
        """
        Qt slot for G slider changes.

        :param value: G slider new value
        :type value: int
        """
        self._ui.G_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_B_slider_valueChanged")
    @log
    def cb_b_slider_changed(self, value):
        """
        Qt slot for B slider changes.

        :param value: B slider new value
        :type value: int
        """
        self._ui.B_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_contrast_slider_valueChanged")
    @log
    def cb_contrast_changed(self, value):
        """
        Qt slot for contrast slider changes.

        :param value: contrast slider new value
        :type value: int
        """
        self._ui.contrast.setNum(value / 10)

    @pyqtSlot(bool, name="on_cbWww_clicked")
    @log
    def cb_www_check(self, checked):
        """
        Qt slot for mouse clicks on 'www' checkbox.

        :param checked: True if the checkbox is checked, False otherwise
        :type checked: bool
        """
        if checked:
            self._start_www()
        else:
            self._stop_www()

    @pyqtSlot(name="on_pbSave_clicked")
    @log
    def cb_save(self):
        """Qt slot for louse clicks on the 'save' button."""

        timestamp = str(datetime.fromtimestamp(datetime.timestamp(datetime.now()))).replace(' ', "-").replace(":", '-')

        save_image(self.image_ref_save.image,
                   config.IMAGE_SAVE_FIT,
                   config.get_work_folder_path(),
                   config.STACKED_IMAGE_FILE_NAME_BASE + '-' + timestamp)

    @pyqtSlot(name="on_pb_apply_value_clicked")
    @log
    def cb_apply_value(self):
        """Qt slot for clicks on the 'apply' button"""
        if self.counter > 0:
            self.adjust_value()
            self.update_image(False)
        self._ui.log.append(_("Define new display value"))

    @pyqtSlot(name="on_action_quit_triggered")
    @log
    def cb_quit(self):
        """ Qt slot for activation of the 'quit' action"""
        super().close()

    @pyqtSlot(name="on_action_prefs_triggered")
    @log
    def cb_prefs(self):
        """ Qt slot for activation of the 'preferences' action"""
        dialog = PreferencesDialog(self)
        dialog.exec()

    @pyqtSlot(name="on_action_about_als_triggered")
    @log
    def cb_about(self):
        """ Qt slot for activation of the 'about' action"""
        dialog = AboutDialog(self)
        dialog.exec()

    @log
    def adjust_value(self):
        """
        Adjusts stacked image according to GUU controls

        """

        # test rgb or gray
        if len(self.image_ref_save.image.shape) == 2:
            mode = "gray"
        elif len(self.image_ref_save.image.shape) == 3:
            mode = "rgb"
        else:
            raise ValueError(_("fit format not supported"))

        self.image_ref_save.stack_image = prepro.post_process_image(self.image_ref_save.image, self._ui.log,
                                                                    mode=mode,
                                                                    scnr_on=self._ui.cbSCNR.isChecked(),
                                                                    wavelets_on=self._ui.cbWavelets.isChecked(),
                                                                    wavelets_type=str(self._ui.cBoxWaveType.currentText()),
                                                                    wavelets_use_luminance=self._ui.cbLuminanceWavelet.isChecked(),
                                                                    param=[self._ui.contrast_slider.value() / 10.,
                                                                           self._ui.brightness_slider.value(),
                                                                           self._ui.black_slider.value(),
                                                                           self._ui.white_slider.value(),
                                                                           self._ui.R_slider.value() / 100.,
                                                                           self._ui.G_slider.value() / 100.,
                                                                           self._ui.B_slider.value() / 100.,
                                                                           self._ui.cmSCNR.currentText(),
                                                                           self._ui.SCNR_Slider.value() / 100.,
                                                                           {1: int(self._ui.wavelet_1_label.text()) / 100.,
                                                                            2: int(self._ui.wavelet_2_label.text()) / 100.,
                                                                            3: int(self._ui.wavelet_3_label.text()) / 100.,
                                                                            4: int(self._ui.wavelet_4_label.text()) / 100.,
                                                                            5: int(self._ui.wavelet_5_label.text()) / 100.}])

        self._ui.log.append(_("Adjust GUI image"))

        save_stack_result(self.image_ref_save.stack_image)

    @log
    def update_image(self, add=True):
        """
        Update central image display.

        :param add: True if a new image has been added to the stack, False otherwise
        """
        if add:
            self.counter += 1
            self._ui.cnt.setText(str(self.counter))
            message = _("update GUI image")
            self._ui.log.append(_(message))
            _LOGGER.info(message)

        if self.counter > 0:
            qimage = array2qimage(cv2.cvtColor(self.image_ref_save.stack_image, cv2.COLOR_BGR2RGB), normalize=(2 ** 16 - 1))
            pixmap = QPixmap.fromImage(qimage)

            if pixmap.isNull():
                self._ui.log.append(_("invalid frame"))
                _LOGGER.error("Got a null pixmap from stack")
                return

            pixmap_resize = pixmap.scaled(self._ui.image_stack.frameGeometry().width(),
                                          self._ui.image_stack.frameGeometry().height(),
                                          Qt.KeepAspectRatio, Qt.SmoothTransformation)

            self._ui.image_stack.setPixmap(pixmap_resize)

        else:
            self._ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))

    @pyqtSlot(name="on_pbPlay_clicked")
    @log
    def cb_play(self):
        """Qt slot for mouse clicks on the 'play' button"""

        # check existence of work and scan folders
        scan_folder_path = config.get_scan_folder_path()
        if not os.path.exists(scan_folder_path) or not os.path.isdir(scan_folder_path):
            if question("Scan folder issue",
                        f"Your configured scan folder '{scan_folder_path}' is missing.\n"
                        f"Do you want to open preferences screen ?"):
                self.cb_prefs()
            else:
                return

        work_folder_path = config.get_work_folder_path()
        if not os.path.exists(work_folder_path) or not os.path.isdir(work_folder_path):
            if question("Work folder issue",
                        f"Your configured work folder '{work_folder_path}' is missing.\n"
                        f"Do you want to open preferences screen ?"):
                self.cb_prefs()
            else:
                return

        if self.image_ref_save.status == "stop":
            self._ui.white_slider.setEnabled(False)
            self._ui.black_slider.setEnabled(False)
            self._ui.contrast_slider.setEnabled(False)
            self._ui.brightness_slider.setEnabled(False)
            self._ui.R_slider.setEnabled(False)
            self._ui.G_slider.setEnabled(False)
            self._ui.B_slider.setEnabled(False)
            self._ui.pb_apply_value.setEnabled(False)
            self._ui.cbAlign.setEnabled(False)
            self._ui.cmMode.setEnabled(False)
            self._ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))
            self.counter = 0
            self._ui.cnt.setText(str(self.counter))
            # Print scan folder
            self._ui.log.append(_("Scan folder : ") + config.get_scan_folder_path())
            # Print work folder
            self._ui.log.append(_("Work folder : ") + config.get_work_folder_path())

        # check align
        if self._ui.cbAlign.isChecked():
            self.align = True

        # Print live method
        if self.align:
            self._ui.log.append(_("Play with alignement type: ") + self._ui.cmMode.currentText())
        else:
            self._ui.log.append(_("Play with NO alignement"))

        self.file_watcher = WatchOutForFileCreations(config.get_scan_folder_path(),
                                                     config.get_work_folder_path(),
                                                     self.align,
                                                     self._ui.cbKeep.isChecked(),
                                                     self._ui.cmMode.currentText(),
                                                     self._ui.log,
                                                     self._ui.white_slider,
                                                     self._ui.black_slider,
                                                     self._ui.contrast_slider,
                                                     self._ui.brightness_slider,
                                                     self._ui.R_slider,
                                                     self._ui.G_slider,
                                                     self._ui.B_slider,
                                                     self._ui.pb_apply_value,
                                                     self.image_ref_save,
                                                     self._ui.cbSCNR,
                                                     self._ui.cmSCNR,
                                                     self._ui.SCNR_Slider,
                                                     self._ui.cbWavelets,
                                                     self._ui.cBoxWaveType,
                                                     self._ui.cbLuminanceWavelet,
                                                     self._ui.wavelet_1_label,
                                                     self._ui.wavelet_2_label,
                                                     self._ui.wavelet_3_label,
                                                     self._ui.wavelet_4_label,
                                                     self._ui.wavelet_5_label)

        try:
            self._setup_work_folder()
        except OSError as os_error:
            title = "Work folder could not be prepared"
            message = f"Details : {os_error}"
            error_box(title, message)
            _LOGGER.error(f"{title} : {os_error}")
            self.cb_stop()
            return

        self.file_watcher.start()
        self.file_watcher.print_image.connect(
            lambda: self.update_image(config.get_work_folder_path()))

        self.image_ref_save.status = "play"
        self.image_ref_save.image = None
        self.image_ref_save.stack_image = None
        # deactivate play button
        self._ui.pbPlay.setEnabled(False)
        self._ui.pbReset.setEnabled(False)
        # activate stop button
        self._ui.pbStop.setEnabled(True)
        # activate pause button
        self._ui.pbPause.setEnabled(True)

        self._ui.action_prefs.setEnabled(False)

        model.STORE.scan_in_progress = True

    def on_image_save_success(self, message):
        """
        Qt slot for successful image save

        :param message: the message to display
        :type message: str
        """
        self._ui.log.append(message)

    def on_image_save_failure(self, message):
        """
        Qt slot for failed image save

        :param message: the message to display
        :type message: str
        """
        self._ui.log.append(message)

    @log
    def update_store_display(self):
        """
        Updates all displays and controls depending on DataStore held data
        """
        messages = list()

        messages.append(f"Scanning '{config.get_scan_folder_path()}'" if model.STORE.scan_in_progress else "Scanner : idle")

        if model.STORE.web_server_is_running:
            messages.append(f"Web server reachable at http://{MainWindow.get_ip()}:{config.get_www_server_port_number()}")
        else:
            messages.append("Web server : idle")

        self._ui.statusBar.showMessage('   -   '.join(messages))

    @log
    def _setup_work_folder(self):
        """Prepares the work folder."""
        work_dir_path = config.get_work_folder_path()
        resources_dir_path = os.path.dirname(os.path.realpath(__file__)) + "/../resources"
        shutil.copy(resources_dir_path + "/index.html", work_dir_path)
        shutil.copy(resources_dir_path + "/waiting.jpg", work_dir_path + "/" + config.WEB_SERVED_IMAGE_FILE_NAME_BASE + ".jpg")

    @pyqtSlot(name="on_pbStop_clicked")
    @log
    def cb_stop(self):
        """Qt slot for mouse clicks on the 'Stop' button"""
        self.file_watcher.observer.stop()
        self.file_watcher.terminate()
        self.image_ref_save.status = "stop"
        self.image_ref_save.stack_image = None
        self._ui.cbAlign.setEnabled(True)
        self._ui.cmMode.setEnabled(True)
        self._ui.pbStop.setEnabled(False)
        self._ui.pbPlay.setEnabled(True)
        self._ui.pbReset.setEnabled(True)
        self._ui.pbPause.setEnabled(False)
        self._ui.action_prefs.setEnabled(not self._ui.cbWww.isChecked())
        self._ui.log.append("Stop")
        model.STORE.scan_in_progress = False

    @pyqtSlot(name="on_pbPause_clicked")
    @log
    def cb_pause(self):
        """Qt slot for mouse clicks on the 'Pause' button"""
        self.file_watcher.observer.stop()
        self.file_watcher.terminate()
        self.image_ref_save.status = "pause"
        self._ui.pbStop.setEnabled(False)
        self._ui.pbPlay.setEnabled(True)
        self._ui.pbReset.setEnabled(False)
        self._ui.pbPause.setEnabled(False)
        self._ui.log.append("Pause")
        model.STORE.scan_in_progress = False

    @pyqtSlot(name="on_pbReset_clicked")
    @log
    def cb_reset(self):
        """Qt slot for mouse clicks on the 'Reset' button"""
        self._ui.log.append("Reset")
        # reset slider, label, image, global value

        self._ui.contrast_slider.setValue(10)
        self._ui.brightness_slider.setValue(0)
        self._ui.black_slider.setValue(0)
        self._ui.white_slider.setValue(65535)
        self._ui.R_slider.setValue(100)
        self._ui.G_slider.setValue(100)
        self._ui.B_slider.setValue(100)
        self._ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))
        self.image_ref_save.image = None
        self.image_ref_save.stack_image = None
        self._ui.contrast.setText(str(1))
        self._ui.brightness.setText(str(0))
        self._ui.black.setText(str(0))
        self._ui.white.setText(str(65535))
        self.counter = 0
        self._ui.cnt.setText(str(self.counter))
        self._ui.white_slider.setEnabled(False)
        self._ui.black_slider.setEnabled(False)
        self._ui.contrast_slider.setEnabled(False)
        self._ui.brightness_slider.setEnabled(False)
        self._ui.R_slider.setEnabled(False)
        self._ui.G_slider.setEnabled(False)
        self._ui.B_slider.setEnabled(False)
        self._ui.pb_apply_value.setEnabled(False)
        self._ui.cbSCNR.setChecked(False)
        self._ui.cbWavelets.setChecked(False)
        self._ui.cbLuminanceWavelet.setChecked(False)

    @pyqtSlot(bool, name="on_log_dock_visibilityChanged")
    @log
    def cb_log_dock_changed_visibility(self, visible):
        """
        Qt slot for changes of log dock visibility.

        :param visible: True if log dock is visible
        :type visible: bool
        """

        if not self.windowState() & Qt.WindowMinimized:
            self.shown_log_dock = visible
            QTimer.singleShot(1, self.update_image_after_dock_change)

    @pyqtSlot(bool, name="on_session_dock_visibilityChanged")
    @log
    def cb_session_dock_changed_visibility(self, visible):
        """
        Qt slot for changes of session dock visibility.

        :param visible: True if session dock is visible
        :type visible: bool
        """

        if not self.windowState() & Qt.WindowMinimized:
            self.show_session_dock = visible
            QTimer.singleShot(1, self.update_image_after_dock_change)

    @log
    def update_image_after_dock_change(self):
        """
        Updates central image display
        """
        self.update_image(False)

    @log
    def _start_www(self):
        """Starts web server"""
        self.web_dir = config.get_work_folder_path()
        ip_address = MainWindow.get_ip()
        port_number = config.get_www_server_port_number()
        try:
            self.thread = StoppableServerThread(self.web_dir)
            self.thread.start()

            # Server is now started and listens on specified port on *all* available interfaces.
            # We get the machine ip address and warn user if detected ip is loopback (127.0.0.1)
            # since in this case, the web server won't be reachable by any other machine
            if ip_address == "127.0.0.1":
                log_function = _LOGGER.warning
                title = "Web server access is limited"
                message = "Web server IP address is 127.0.0.1.\n\nServer won't be reachable by other " \
                          "machines. Please check your network connection"
                warning_box(title, message)
            else:
                log_function = _LOGGER.info

            log_function(f"Web server started. http://{ip_address}:{port_number}")
            self._ui.action_prefs.setEnabled(False)
            model.STORE.web_server_is_running = True
        except OSError:
            title = "Could not start web server"
            message = f"The web server needs to listen on port n°{port_number} but this port is already in use.\n\n"
            message += "Please change web server port number in your preferences "
            _LOGGER.error(title)
            error_box(title, message)
            self._stop_www()
            self._ui.cbWww.setChecked(False)

    @log
    def _stop_www(self):
        """Stops web server"""
        if self.thread:
            self.thread.stop()
            self.thread.join()
            self.thread = None
            _LOGGER.info("Web server stopped")
            model.STORE.web_server_is_running = False
            self._ui.action_prefs.setEnabled(self._ui.pbPlay.isEnabled())

    @staticmethod
    @log
    def get_ip():
        """
        Retrieves machine's IP address.

        :return: IP address
        :rtype: str
        """
        import socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            test_socket.connect(('10.255.255.255', 1))
            ip_address = test_socket.getsockname()[0]
        except OSError:
            ip_address = '127.0.0.1'
        finally:
            test_socket.close()
        return ip_address


@log
def save_stack_result(image):
    """
    Saves stacking result image to disk

    :param image: the image to save
    :type image: numpy.Array
    """

    # we save the image no matter what, then save a jpg for the webserver if it is running
    save_image(image,
               config.get_image_save_format(),
               config.get_work_folder_path(),
               config.STACKED_IMAGE_FILE_NAME_BASE)

    if STORE.web_server_is_running:
        save_image(image,
                   config.IMAGE_SAVE_JPEG,
                   config.get_work_folder_path(),
                   config.WEB_SERVED_IMAGE_FILE_NAME_BASE)


def main():
    """app launcher"""
    app = QApplication(sys.argv)

    _LOGGER.info(f"Starting Astro Live Stacker v{VERSION} in {os.path.dirname(os.path.realpath(__file__))}")

    _LOGGER.debug("Building and showing main window")
    window = MainWindow()

    (x, y, width, height) = config.get_window_geometry()
    window.setGeometry(x, y, width, height)
    window.show()

    app_return_code = app.exec()
    _LOGGER.info(f"Astro Live Stacker terminated with return code = {app_return_code}")
    sys.exit(app_return_code)


if __name__ == "__main__":
    main()
