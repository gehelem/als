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

import numpy as np
import cv2
from PyQt5.QtCore import Qt, pyqtSlot, QEvent
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication, QGraphicsScene, QGraphicsPixmapItem
from astroalign import MaxIterError
from astropy.io import fits
from qimage2ndarray import array2qimage
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from als.code_utilities import log, Timer
from als.io.output import ImageSaver, save_image
from als import preprocess as prepro, config, model
from als.processing import PreProcessPipeline
from als.io.input import ScannerStartError, InputScanner
from als.model import VERSION, STORE, STACKING_MODE_SUM, STACKING_MODE_MEAN
from als.stack import Stacker
from als.ui import dialogs
from als.ui.dialogs import PreferencesDialog, question, error_box, warning_box, AboutDialog
from generated.als_ui import Ui_stack_window
from qimage2ndarray import array2qimage

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


class MainWindow(QMainWindow):
    """
    ALS main window.

    It also acts as the main controller, for now
    """

    @log
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_stack_window()
        self._ui.setupUi(self)

        self._ui.cb_stacking_mode.addItem(STACKING_MODE_SUM)
        self._ui.cb_stacking_mode.addItem(STACKING_MODE_MEAN)
        self._ui.cb_stacking_mode.setCurrentIndex(0)

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

        model.STORE.scan_in_progress = False
        model.STORE.web_server_is_running = False
        model.STORE.add_observer(self)

        self._image_saver = ImageSaver()
        self._image_saver.start()

        self._input_scanner = InputScanner.create_scanner(STORE.input_queue)

        self._pre_process_pipeline = PreProcessPipeline(STORE.input_queue, STORE.stack_queue)
        self._pre_process_pipeline.start()

        self._stacker = Stacker(STORE.stack_queue)
        self._stacker.start()
        self._stacker.stack_size_changed_signal[int].connect(self.on_stack_size_changed)
        self._stacker.stack_result_ready_signal.connect(self.on_new_stack_result)

        self.update_store_display()

        STORE.input_queue.item_pushed_signal[int].connect(self.on_input_queue_pushed)
        STORE.input_queue.item_popped_signal[int].connect(self.on_input_queue_popped)

        STORE.stack_queue.item_pushed_signal[int].connect(self.on_stack_queue_pushed)
        STORE.stack_queue.item_popped_signal[int].connect(self.on_stack_queue_popped)

        self._scene = QGraphicsScene(self)
        self._ui.image_view.setScene(self._scene)
        self._image_item = None

        self.reset_image_view()

    @log
    def reset_image_view(self):
        for item in self._scene.items():
            self._scene.removeItem(item)
        self._image_item = QGraphicsPixmapItem(QPixmap(":/icons/dslr-camera.svg"))
        self._scene.addItem(self._image_item)
        self._ui.image_view.fitInView(self._image_item, Qt.KeepAspectRatio)

    @log
    def closeEvent(self, event):
        """Handles window close events."""
        # pylint: disable=C0103

        if STORE.web_server_is_running:
            self._stop_www()
        if STORE.session_is_started:
            self.cb_stop()

        self._pre_process_pipeline.stop()

        self._stacker.stop()

        _LOGGER.debug(f"Window size : {self.size()}")
        _LOGGER.debug(f"Window position : {self.pos()}")

        window_rect = self.geometry()
        config.set_window_geometry((window_rect.x(), window_rect.y(), window_rect.width(), window_rect.height()))
        config.save()

        self._image_saver.stop()

        if self._image_saver.isRunning():
            message = "Making sure all images are saved..."
            _LOGGER.info(message)
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
        pass
        # super().resizeEvent(event)
        # self.update_image(False)

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
        """
        Qt slot for louse clicks on the 'save' button.

        This saves the processed image using user chosen format

        """
        if self.image_ref_save.image is not None:
            save_image(self.image_ref_save.image,
                       config.get_image_save_format(),
                       config.get_work_folder_path(),
                       config.STACKED_IMAGE_FILE_NAME_BASE + '-' + _get_timestamp())

    @pyqtSlot(name="on_pb_apply_value_clicked")
    @log
    def cb_apply_value(self):
        """Qt slot for clicks on the 'apply' button"""
        if self.counter > 0:
            self.adjust_value()
            self.update_image(False)
        _LOGGER.info("Define new display value")

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
    def on_input_queue_pushed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the input queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.info(f"New image added to the input queue. Input queue size : {new_size}")
        self._ui.lbl_input_queue_size.setText(str(new_size))

    @log
    def on_input_queue_popped(self, new_size):
        """
        Qt slot executed when an item has just been popped from the input queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.info(f"Image taken from input queue. Input queue size : {new_size}")
        self._ui.lbl_input_queue_size.setText(str(new_size))

    @log
    def on_stack_queue_pushed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the stack queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.info(f"New image added to the stack queue. Stack queue size : {new_size}")
        self._ui.lbl_stack_queue_size.setText(str(new_size))

    @log
    def on_stack_queue_popped(self, new_size):
        """
        Qt slot executed when an item has just been popped from the stack queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.info(f"Image taken from stack queue. Stack queue size : {new_size}")
        self._ui.lbl_stack_queue_size.setText(str(new_size))

    @log
    def on_stack_size_changed(self, new_size: int):
        """
        Qt slot executed when stack size changed

        :param new_size: new stack size
        :type new_size: int
        """
        self._ui.cnt.setText(str(new_size))

    # pylint: disable=C0103
    @log
    def on_cb_stacking_mode_currentTextChanged(self, text: str):
        """
        Qt slot executed when stacking mode comb box changed

        :param text: new stacking mode
        :type text: str
        :return:
        """
        STORE.stacking_mode = text

    @log
    def on_chk_align_toggled(self, checked: bool):
        """
        Qt slot executed when 'align' check box is changed

        :param checked: is checkbox checked ?
        :type checked: bool
        """
        STORE.align_before_stacking = checked

    @log
    def on_new_stack_result(self):
        """
        Qt slot executed when a new stacking result is available
        """
        _LOGGER.info(f"New Stacking result available : {STORE.stacking_result}")
        self.update_image()

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

        self.image_ref_save.stack_image = prepro.post_process_image(self.image_ref_save.image,
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

        _LOGGER.info("Adjust GUI image")

        save_stack_result(self.image_ref_save.stack_image)

    @log
    def update_image(self, add=True):
        """
        Update central image display.

        :param add: True if a new image has been added to the stack, False otherwise
        """
        image = STORE.stacking_result
        image_raw_data = image.data.copy()

        if image.is_color():
            # TODO : move this outside of GUI code
            image_raw_data = np.moveaxis(image_raw_data, 0, 2)

        image = array2qimage(image_raw_data, normalize=(2 ** 16 - 1))
        self._image_item.setPixmap(QPixmap.fromImage(image))

        # if add:
        #     self.counter += 1
        #     self._ui.cnt.setText(str(self.counter))
        #     message = _("update GUI image")
        #     self._ui.log.append(_(message))
        #     _LOGGER.info(message)
        #
        # if self.counter > 0:
        #
        #     # read image in RAM ( need save_type = "no"):
        #     qimage = array2qimage(self.image_ref_save.stack_image, normalize=(2 ** 16 - 1))
        #     pixmap = QPixmap.fromImage(qimage)
        #
        #     if pixmap.isNull():
        #         self._ui.log.append(_("invalid frame"))
        #         _LOGGER.error("Got a null pixmap from stack")
        #         return
        #
        #     pixmap_resize = pixmap.scaled(self._ui.image_stack.frameGeometry().width(),
        #                                   self._ui.image_stack.frameGeometry().height(),
        #                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
        #
        #     self._ui.image_stack.setPixmap(pixmap_resize)
        #
        # else:
        #     self._ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))

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
            self._ui.chk_align.setEnabled(False)
            self._ui.cb_stacking_mode.setEnabled(False)
            self.counter = 0
            self._ui.cnt.setText(str(self.counter))

        # check align
        if self._ui.chk_align.isChecked():
            self.align = True

        # Print live method
        if self.align:
            _LOGGER.info(f"Play with alignement type: {self._ui.cb_stacking_mode.currentText()}")
        else:
            _LOGGER.info("Play with NO alignement")

        try:
            self._setup_work_folder()
        except OSError as os_error:
            title = "Work folder could not be prepared"
            message = f"Details : {os_error}"
            error_box(title, message)
            _LOGGER.error(f"{title} : {os_error}")
            self.cb_stop()
            return

        self.image_ref_save.status = "play"
        self.image_ref_save.image = None
        self.image_ref_save.stack_image = None

        _LOGGER.info(f"Work folder : '{config.get_work_folder_path()}'")
        _LOGGER.info(f"Scan folder : '{config.get_scan_folder_path()}'")

        try:
            self._input_scanner.start()
            STORE.record_session_start()
        except ScannerStartError as start_error:
            dialogs.error_box("Could not start folder scanner", str(start_error))

    def on_log_message(self, message):
        """
        print received log message to GUI log window

        :param message: the log message
        :type message: str
        """
        self._ui.log.addItem(message)
        self._ui.log.scrollToBottom()

    @log
    def update_according_to_app_state(self):
        """
        Updates all displays and controls depending on DataStore held data
        """

        # build status bar messages display
        messages = list()

        # update statusBar according to status of folder scanner and web server
        messages.append(f"Scanning '{config.get_scan_folder_path()}'" if STORE.session_is_started else "Scanner : idle")

        if STORE.web_server_is_running:
            messages.append(f"Web server reachable at "
                            f"http://{MainWindow.get_ip()}:{config.get_www_server_port_number()}")
        else:
            messages.append("Web server : idle")

        self._ui.statusBar.showMessage('   -   '.join(messages))

        # update preferences accessibility according to scanner and webserver status
        self._ui.action_prefs.setEnabled(not STORE.web_server_is_running and not STORE.scan_in_progress)

        # handle Start / Pause / Stop buttons
        self._ui.pbPlay.setEnabled(STORE.session_is_stopped or STORE.session_is_paused)
        self._ui.pbReset.setEnabled(STORE.session_is_stopped)
        self._ui.pbStop.setEnabled(STORE.session_is_started or STORE.session_is_paused)
        self._ui.pbPause.setEnabled(STORE.session_is_started)

    @log
    def _setup_work_folder(self):
        """Prepares the work folder."""

        work_dir_path = config.get_work_folder_path()
        resources_dir_path = os.path.dirname(os.path.realpath(__file__)) + "/../resources"

        shutil.copy(resources_dir_path + "/index.html", work_dir_path)

        standby_image_path = work_dir_path + "/" + config.WEB_SERVED_IMAGE_FILE_NAME_BASE + '.' + config.IMAGE_SAVE_JPEG
        shutil.copy(resources_dir_path + "/waiting.jpg", standby_image_path)

    @pyqtSlot(name="on_pbStop_clicked")
    @log
    def cb_stop(self):
        """Qt slot for mouse clicks on the 'Stop' button"""
        self.image_ref_save.status = "stop"
        self._ui.chk_align.setEnabled(True)
        self._ui.cb_stacking_mode.setEnabled(True)
        self._ui.action_prefs.setEnabled(not self._ui.cbWww.isChecked())
        _LOGGER.info("Stop")
        self._input_scanner.stop()
        self._purge_input_queue()
        STORE.record_session_stop()

    @pyqtSlot(name="on_pbPause_clicked")
    @log
    def cb_pause(self):
        """Qt slot for mouse clicks on the 'Pause' button"""
        self.image_ref_save.status = "pause"
        _LOGGER.info("Pause")
        self._input_scanner.stop()
        STORE.record_session_pause()

    @pyqtSlot(name="on_pbReset_clicked")
    @log
    def cb_reset(self):
        """Qt slot for mouse clicks on the 'Reset' button"""
        _LOGGER.info("Reset")
        # reset slider, label, image, global value

        self._ui.contrast_slider.setValue(10)
        self._ui.brightness_slider.setValue(0)
        self._ui.black_slider.setValue(0)
        self._ui.white_slider.setValue(65535)
        self._ui.R_slider.setValue(100)
        self._ui.G_slider.setValue(100)
        self._ui.B_slider.setValue(100)
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

        self._stacker.reset()
        self.reset_image_view()

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

            url = f"http://{ip_address}:{port_number}"
            log_function(f"Web server started. Reachable at {url}")
            self._ui.action_prefs.setEnabled(False)
            QApplication.clipboard().setText(url)
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

    @log
    def _purge_input_queue(self):
        """
        Purge the input queue

        """
        while not STORE.input_queue.empty():
            STORE.input_queue.get()
        _LOGGER.info("Input queue purged")

    @log
    def _purge_stack_queue(self):
        """
        Purge the stack queue

        """
        while not STORE.stack_queue.empty():
            STORE.stack_queue.get()
        _LOGGER.info("Stack queue purged")

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


def _get_timestamp():
    timestamp = str(datetime.fromtimestamp(datetime.timestamp(datetime.now())))
    timestamp = timestamp.replace(' ', "-").replace(":", '-').replace('.', '-')
    return timestamp

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
    with Timer() as startup:
        app = QApplication(sys.argv)

        config.setup()

        _LOGGER.debug("Building and showing main window")
        window = MainWindow()
        config.register_log_receiver(window)
        (x, y, width, height) = config.get_window_geometry()
        window.setGeometry(x, y, width, height)
        window.show()
        window.reset_image_view()
    _LOGGER.info(f"Astro Live Stacker version {VERSION} started in {startup.elapsed_in_milli} ms.")

    app_return_code = app.exec()
    _LOGGER.info(f"Astro Live Stacker terminated with return code = {app_return_code}")
    sys.exit(app_return_code)


if __name__ == "__main__":
    main()
