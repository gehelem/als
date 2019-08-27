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
import gettext
import logging
import os
import shutil
import threading
from datetime import datetime
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler

import numpy as np
from PyQt5.QtCore import pyqtSignal, QFileInfo, QThread, Qt, pyqtSlot, QTimer, QEvent
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication
from astropy.io import fits
from qimage2ndarray import array2qimage
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import preprocess as prepro
import stack as stk
from alsui import Ui_stack_window  # import du fichier alsui.py généré par : pyuic5 alsui.ui -x -o alsui.py
from code_utilities import log
from datastore import VERSION
from dialogs import PreferencesDialog, question, error_box, warning_box, AboutDialog

NAME_OF_TIFF_IMAGE = "stack_image.tiff"
NAME_OF_JPEG_IMAGE = "stack_image.jpg"
NAME_OF_PNG_IMAGE = "stack_image.png"
SAVE_TYPE = "png"
DEFAULT_SCAN_SIZE_RETRY_PERIOD_MS = 100
LOG_DOCK_INITIAL_HEIGHT = 60

gettext.install('als', 'locale')

_logger = logging.getLogger(__name__)


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
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

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
        while not self.stopped():
            self.httpd.handle_request()

    @log
    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class ImageRefSave:
    @log
    def __init__(self):
        self.image = []
        self.status = "stop"
        self.stack_image = []


class MyEventHandler(FileSystemEventHandler, QThread, ImageRefSave):
    created_signal = pyqtSignal(str)

    @log
    def __init__(self):
        super().__init__()

    @log
    def on_moved(self, event):
        if event.event_type == 'moved':
            image_path = event.dest_path
            _logger.info(f"New image ready to be processed : {image_path}")
            _logger.debug(f"created signal emitted from on_moved : {image_path}")
            self.created_signal.emit(image_path)

    @log
    def on_created(self, event):
        if event.event_type == 'created':
            file_is_incomplete = True
            last_file_size = -1
            image_path = event.src_path
            _logger.debug(f"New image file detected : {image_path}. Waiting untill file is fully written to disk...")

            while file_is_incomplete:
                info = QFileInfo(image_path)
                size = info.size()
                _logger.debug(f"File {image_path}'s size = {size}")
                if size == last_file_size:
                    file_is_incomplete = False
                    _logger.debug(f"File {image_path} has been fully written to disk")
                last_file_size = size
                self.msleep(DEFAULT_SCAN_SIZE_RETRY_PERIOD_MS)

            _logger.info(f"New image ready to be processed : {image_path}")
            _logger.debug(f"created signal emitted from on_created : {image_path}")
            self.created_signal.emit(image_path)


# ------------------------------------------------------------------------------


class WatchOutForFileCreations(QThread):
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
        self.first_image = []
        self.image_ref_save = image_ref_save
        self.ref_image = []
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
        _logger.info(f" Work folder = '{self.work_folder}'")
        _logger.info(f" Scan folder = '{self.path}'")

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

                self.image_ref_save.stack_image = prepro.save_tiff(self.work_folder, self.image_ref_save.image,
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
                                                                           5: int(self.wavelet_5_value.text()) / 100.}],
                                                                   image_type=SAVE_TYPE)
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
                # appelle de la fonction stack live
                if self.align_on:
                    self.log.append(_("Stack and Align New frame..."))
                else:
                    self.log.append(_("Stack New frame..."))

                self.image_ref_save.image, limit, mode = stk.stack_live(self.work_folder, new_image_path,
                                                                        self.counter,
                                                                        ref=self.image_ref_save.image,
                                                                        first_ref=self.first_image,
                                                                        save_im=self.save_on,
                                                                        align=self.align_on,
                                                                        stack_methode=self.stack_method)

                self.image_ref_save.stack_image = prepro.save_tiff(self.work_folder, self.image_ref_save.image,
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
                                                                           5: int(self.wavelet_5_value.text()) / 100.}],
                                                                   image_type=SAVE_TYPE)

                self.log.append(_("... Stack finished"))
            self.print_image.emit()
        else:
            message = _("New image detected but not considered")
            self.log.append(message)
            _logger.info(message)


# ------------------------------------------------------------------------------


class MainWindow(QMainWindow):

    @log
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_stack_window()
        self.ui.setupUi(self)

        # store if docks must be shown or not
        self.shown_log_dock = True
        self.show_session_dock = True

        self.running = False
        self.counter = 0
        self.align = False
        self.pause = False
        self.image_ref_save = ImageRefSave()
        self.ui.postprocess_widget.setCurrentIndex(0)

        self.setWindowTitle(_("Astro Live Stacker") + f" - v{VERSION}")

        # web stuff
        self.thread = None
        self.web_dir = None

        # prevent log dock to be too tall
        self.resizeDocks([self.ui.log_dock], [LOG_DOCK_INITIAL_HEIGHT], Qt.Vertical)

    @log
    def closeEvent(self, event):
        self._stop_www()

        _logger.debug(f"Window size : {self.size()}")
        _logger.debug(f"Window position : {self.pos()}")

        window_rect = window.geometry()
        config.set_window_geometry((window_rect.x(), window_rect.y(), window_rect.width(), window_rect.height()))
        config.save()

        super().closeEvent(event)

    @log
    def changeEvent(self, event):

        event.accept()

        # if window is going out of minimized state, we restore docks if needed
        if event.type() == QEvent.WindowStateChange:
            if not self.windowState() & Qt.WindowMinimized:
                _logger.debug("Restoring docks visibility")
                if self.shown_log_dock:
                    self.ui.log_dock.show()
                if self.show_session_dock:
                    self.ui.session_dock.show()

    @log
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image(False)

    # ------------------------------------------------------------------------------
    # Callbacks

    @pyqtSlot(int, name="on_SCNR_Slider_valueChanged")
    @log
    def cb_scnr_slider_changed(self, value):
        self.ui.SCNR_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_R_slider_valueChanged")
    @log
    def cb_r_slider_changed(self, value):
        self.ui.R_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_G_slider_valueChanged")
    @log
    def cb_g_slider_changed(self, value):
        self.ui.G_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_B_slider_valueChanged")
    @log
    def cb_b_slider_changed(self, value):
        self.ui.B_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_contrast_slider_valueChanged")
    @log
    def cb_contrast_changed(self, value):
        self.ui.contrast.setNum(value / 10)

    @pyqtSlot(bool, name="on_cbWww_clicked")
    @log
    def cb_www_check(self, checked):
        if checked:
            self._start_www()
        else:
            self._stop_www()

    @pyqtSlot(name="on_pbSave_clicked")
    @log
    def cb_save(self):
        timestamp = str(datetime.fromtimestamp(datetime.timestamp(datetime.now())))
        self.ui.log.append(_("Saving : ") + "stack_image_" + timestamp + ".fit")
        # save stack image in fit
        red = fits.PrimaryHDU(data=self.image_ref_save.image)
        red.writeto(config.get_work_folder_path() + "/" + "stack_image_" + timestamp + ".fit")
        # red.close()
        del red

    @pyqtSlot(name="on_pb_apply_value_clicked")
    @log
    def cb_apply_value(self):
        work_folder = config.get_work_folder_path()
        if self.counter > 0:
            self.adjust_value(work_folder)
            self.update_image(False)
        self.ui.log.append(_("Define new display value"))

    @pyqtSlot(name="on_action_quit_triggered")
    @log
    def cb_quit(self):
        super().close()

    @pyqtSlot(name="on_action_prefs_triggered")
    @log
    def cb_prefs(self):
        dialog = PreferencesDialog(self)
        dialog.exec()

    @pyqtSlot(name="on_action_about_als_triggered")
    @log
    def cb_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    @log
    def adjust_value(self, work_folder):

        # test rgb or gray
        if len(self.image_ref_save.image.shape) == 2:
            mode = "gray"
        elif len(self.image_ref_save.image.shape) == 3:
            mode = "rgb"
        else:
            raise ValueError(_("fit format not supported"))

        self.image_ref_save.stack_image = prepro.save_tiff(work_folder, self.image_ref_save.image, self.ui.log,
                                                           mode=mode,
                                                           scnr_on=self.ui.cbSCNR.isChecked(),
                                                           wavelets_on=self.ui.cbWavelets.isChecked(),
                                                           wavelets_type=str(self.ui.cBoxWaveType.currentText()),
                                                           wavelets_use_luminance=self.ui.cbLuminanceWavelet.isChecked(),
                                                           param=[self.ui.contrast_slider.value() / 10.,
                                                                  self.ui.brightness_slider.value(),
                                                                  self.ui.black_slider.value(),
                                                                  self.ui.white_slider.value(),
                                                                  self.ui.R_slider.value() / 100.,
                                                                  self.ui.G_slider.value() / 100.,
                                                                  self.ui.B_slider.value() / 100.,
                                                                  self.ui.cmSCNR.currentText(),
                                                                  self.ui.SCNR_Slider.value() / 100.,
                                                                  {1: int(self.ui.wavelet_1_label.text()) / 100.,
                                                                   2: int(self.ui.wavelet_2_label.text()) / 100.,
                                                                   3: int(self.ui.wavelet_3_label.text()) / 100.,
                                                                   4: int(self.ui.wavelet_4_label.text()) / 100.,
                                                                   5: int(self.ui.wavelet_5_label.text()) / 100.}],
                                                           image_type=SAVE_TYPE)

        self.ui.log.append(_("Adjust GUI image"))

    @log
    def update_image(self, add=True):
        if add:
            self.counter += 1
            self.ui.cnt.setText(str(self.counter))
            message = _("update GUI image")
            self.ui.log.append(_(message))
            _logger.info(message)

        if 0 < self.counter:

            # read image in RAM ( need save_type = "no"):
            qimage = array2qimage(self.image_ref_save.stack_image, normalize=(2 ** 16 - 1))
            pixmap = QPixmap.fromImage(qimage)

            if pixmap.isNull():
                self.ui.log.append(_("invalid frame"))
                _logger.error("Got a null pixmap from stack")
                return

            pixmap_resize = pixmap.scaled(self.ui.image_stack.frameGeometry().width(),
                                          self.ui.image_stack.frameGeometry().height(),
                                          Qt.KeepAspectRatio, Qt.SmoothTransformation)

            self.ui.image_stack.setPixmap(pixmap_resize)

        else:
            self.ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))

    @pyqtSlot(name="on_pbPlay_clicked")
    @log
    def cb_play(self):

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
            self.ui.white_slider.setEnabled(False)
            self.ui.black_slider.setEnabled(False)
            self.ui.contrast_slider.setEnabled(False)
            self.ui.brightness_slider.setEnabled(False)
            self.ui.R_slider.setEnabled(False)
            self.ui.G_slider.setEnabled(False)
            self.ui.B_slider.setEnabled(False)
            self.ui.pb_apply_value.setEnabled(False)
            self.ui.cbAlign.setEnabled(False)
            self.ui.cmMode.setEnabled(False)
            self.ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))
            self.counter = 0
            self.ui.cnt.setText(str(self.counter))
            # Print scan folder
            self.ui.log.append(_("Scan folder : ") + config.get_scan_folder_path())
            # Print work folder
            self.ui.log.append(_("Work folder : ") + config.get_work_folder_path())

        # check align
        if self.ui.cbAlign.isChecked():
            self.align = True

        # Print live method
        if self.align:
            self.ui.log.append(_("Play with alignement type: ") + self.ui.cmMode.currentText())
        else:
            self.ui.log.append(_("Play with NO alignement"))

        self.file_watcher = WatchOutForFileCreations(config.get_scan_folder_path(),
                                                     config.get_work_folder_path(),
                                                     self.align,
                                                     self.ui.cbKeep.isChecked(),
                                                     self.ui.cmMode.currentText(),
                                                     self.ui.log,
                                                     self.ui.white_slider,
                                                     self.ui.black_slider,
                                                     self.ui.contrast_slider,
                                                     self.ui.brightness_slider,
                                                     self.ui.R_slider,
                                                     self.ui.G_slider,
                                                     self.ui.B_slider,
                                                     self.ui.pb_apply_value,
                                                     self.image_ref_save,
                                                     self.ui.cbSCNR,
                                                     self.ui.cmSCNR,
                                                     self.ui.SCNR_Slider,
                                                     self.ui.cbWavelets,
                                                     self.ui.cBoxWaveType,
                                                     self.ui.cbLuminanceWavelet,
                                                     self.ui.wavelet_1_label,
                                                     self.ui.wavelet_2_label,
                                                     self.ui.wavelet_3_label,
                                                     self.ui.wavelet_4_label,
                                                     self.ui.wavelet_5_label)

        try:
            self._setup_work_folder()
        except OSError as e:
            title = "Work folder could not be prepared"
            message = f"Details : {e}"
            error_box(title, message)
            _logger.error(f"{title} : {e}")
            self.cb_stop()
            return

        self.file_watcher.start()
        self.file_watcher.print_image.connect(
            lambda: self.update_image(config.get_work_folder_path()))

        self.image_ref_save.status = "play"
        self.image_ref_save.image = []
        self.image_ref_save.stack_image = []
        # desactivate play button
        self.ui.pbPlay.setEnabled(False)
        self.ui.pbReset.setEnabled(False)
        # activate stop button
        self.ui.pbStop.setEnabled(True)
        # activate pause button
        self.ui.pbPause.setEnabled(True)

        self.ui.action_prefs.setEnabled(False)

    @log
    def _setup_work_folder(self):
        work_dir_path = config.get_work_folder_path()
        resources_dir_path = os.path.dirname(os.path.realpath(__file__)) + "/resources_dir"
        shutil.copy(resources_dir_path + "/index.html", work_dir_path)
        shutil.copy(resources_dir_path + "/waiting.jpg", work_dir_path + "/" + NAME_OF_JPEG_IMAGE)

    @pyqtSlot(name="on_pbStop_clicked")
    @log
    def cb_stop(self):
        self.file_watcher.observer.stop()
        # FIXME : this bad but better than app crash
        self.file_watcher.terminate()
        self.image_ref_save.status = "stop"
        self.image_ref_save.stack_image = []
        self.ui.cbAlign.setEnabled(True)
        self.ui.cmMode.setEnabled(True)
        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        self.ui.pbReset.setEnabled(True)
        self.ui.pbPause.setEnabled(False)
        self.ui.action_prefs.setEnabled(not self.ui.cbWww.isChecked())
        self.ui.log.append("Stop")

    @pyqtSlot(name="on_pbPause_clicked")
    @log
    def cb_pause(self):
        # self.fileWatcher.observer.stop()
        self.image_ref_save.status = "pause"
        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        self.ui.pbReset.setEnabled(False)
        self.ui.pbPause.setEnabled(False)
        self.ui.log.append("Pause")

    @pyqtSlot(name="on_pbReset_clicked")
    @log
    def cb_reset(self):
        self.ui.log.append("Reset")
        # reset slider, label, image, global value

        self.ui.contrast_slider.setValue(10)
        self.ui.brightness_slider.setValue(0)
        self.ui.black_slider.setValue(0)
        self.ui.white_slider.setValue(65535)
        self.ui.R_slider.setValue(100)
        self.ui.G_slider.setValue(100)
        self.ui.B_slider.setValue(100)
        self.ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))
        self.image_ref_save.image = []
        self.image_ref_save.stack_image = []
        self.ui.contrast.setText(str(1))
        self.ui.brightness.setText(str(0))
        self.ui.black.setText(str(0))
        self.ui.white.setText(str(65535))
        self.counter = 0
        self.ui.cnt.setText(str(self.counter))
        self.ui.white_slider.setEnabled(False)
        self.ui.black_slider.setEnabled(False)
        self.ui.contrast_slider.setEnabled(False)
        self.ui.brightness_slider.setEnabled(False)
        self.ui.R_slider.setEnabled(False)
        self.ui.G_slider.setEnabled(False)
        self.ui.B_slider.setEnabled(False)
        self.ui.pb_apply_value.setEnabled(False)
        self.ui.cbSCNR.setChecked(False)
        self.ui.cbWavelets.setChecked(False)
        self.ui.cbLuminanceWavelet.setChecked(False)

    @pyqtSlot(bool, name="on_log_dock_visibilityChanged")
    @log
    def cb_log_dock_changed_visibility(self, visible):

        if not self.windowState() & Qt.WindowMinimized:
            self.shown_log_dock = visible
            QTimer.singleShot(1, self.update_image_after_dock_change)

    @pyqtSlot(bool, name="on_session_dock_visibilityChanged")
    @log
    def cb_session_dock_changed_visibility(self, visible):

        if not self.windowState() & Qt.WindowMinimized:
            self.show_session_dock = visible
            QTimer.singleShot(1, self.update_image_after_dock_change)

    @log
    def update_image_after_dock_change(self):
        self.update_image(False)

    @log
    def _start_www(self):
        self.web_dir = config.get_work_folder_path()
        ip_address = MainWindow.get_ip()
        port_number = config.get_www_server_port_number()
        try:
            self.thread = StoppableServerThread(self.web_dir)
            self.thread.start()

            # Server is now started and listens on specified port on *all* available interfaces.
            # We get the machine ip address and warn user if detected ip is loopback (127.0.0.1)
            # since in this case, the web server won't be reachable by any other machine
            if "127.0.0.1" == ip_address:
                log_function = _logger.warning
                title = "Web server access is limited"
                message = "Web server IP address is 127.0.0.1.\n\nServer won't be reachable by other " \
                          "machines. Please check your network connection"
                warning_box(title, message)
            else:
                log_function = _logger.info

            log_function(f"Web server started. http://{ip_address}:{port_number}")
            self.ui.action_prefs.setEnabled(False)
        except OSError:
            title = "Could not start web server"
            message = f"The web server needs to listen on port n°{port_number} but this port is already in use.\n\n"
            message += "Please change web server port number in your preferences "
            _logger.error(title)
            error_box(title, message)
            self._stop_www()
            self.ui.cbWww.setChecked(False)

    @log
    def _stop_www(self):
        if self.thread:
            self.thread.stop()
            self.thread.join()
            self.thread = None
            _logger.info("Web server stopped")
            self.ui.action_prefs.setEnabled(self.ui.pbPlay.isEnabled())

    @staticmethod
    @log
    def get_ip():
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    @log
    def main(self):
        self.show()


# ------------------------------------------------------------------------------


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    try:
        import config
    except ValueError as e:
        error_box("Config file is invalid", str(e))
        print(f"***** ERROR : user config file is invalid : {e}")
        sys.exit(1)

    _logger.info(f"Starting Astro Live Stacker v{VERSION} in {os.path.dirname(os.path.realpath(__file__))}")
    _logger.debug("Building and showing main window")
    window = MainWindow()
    (x, y, width, height) = config.get_window_geometry()
    window.setGeometry(x, y, width, height)
    window.show()
    app_return_code = app.exec()
    _logger.info(f"Astro Live Stacker terminated with return code = {app_return_code}")
    sys.exit(app_return_code)
