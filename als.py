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
from PyQt5.QtCore import pyqtSignal, QFileInfo, QThread, Qt, pyqtSlot
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QApplication, QMessageBox
from astropy.io import fits
from qimage2ndarray import array2qimage
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import messaging
import preprocess as prepro
import stack as stk
from alsui import Ui_stack_window  # import du fichier alsui.py généré par : pyuic5 alsui.ui -x -o alsui.py
from code_utilities import log
from datastore import VERSION

NAME_OF_TIFF_IMAGE = "stack_image.tiff"
NAME_OF_JPEG_IMAGE = "stack_image.jpg"
NAME_OF_PNG_IMAGE = "stack_image.png"
SAVE_TYPE = "png"
DEFAULT_SCAN_SIZE_RETRY_PERIOD_MS = 100

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
    created_signal = pyqtSignal()
    new_image_path = ""

    @log
    def __init__(self):
        super().__init__()

    @log
    def on_created(self, event):
        if event.event_type == 'created':
            file_is_incomplete = True
            last_file_size = -1
            file_path = event.src_path
            _logger.debug(f"New image file detected : {file_path}. Waiting untill file is fully written to disk...")

            while file_is_incomplete:
                info = QFileInfo(file_path)
                size = info.size()
                _logger.debug(f"File {file_path}'s size = {size}")
                if size == last_file_size:
                    file_is_incomplete = False
                    _logger.debug(f"File {file_path} has been fully written to disk")
                last_file_size = size
                self.msleep(DEFAULT_SCAN_SIZE_RETRY_PERIOD_MS)

            _logger.info(f"New image ready to be processed : {file_path}")
            self.new_image_path = file_path
            self.created_signal.emit()


# ------------------------------------------------------------------------------


class WatchOutForFileCreations(QThread):
    print_image = pyqtSignal()

    @log
    def __init__(self, path, work_folder, align_on, save_on, stack_methode,
                 log_ui, white_slider, black_slider, contrast_slider, brightness_slider,
                 r_slider, g_slider, b_slider, apply_button,
                 image_ref_save, dark_on, dark_path,
                 scnr_on, scnr_mode, scnr_value,
                 wavelets_on, wavelets_type, wavelets_use_luminance,
                 wavelet_1_value, wavelet_2_value, wavelet_3_value,
                 wavelet_4_value, wavelet_5_value):

        super().__init__()
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
        self.dark_on = dark_on  # need add dark in stack_live function
        self.dark_path = dark_path  # need add dark in stack_live function
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

        self.event_handler.created_signal.connect(lambda: self.created(self.event_handler.new_image_path,
                                                                       align_on, save_on, stack_methode))

    @log
    def created(self, new_image_path, align_on, save_on, stack_methode):
        if self.image_ref_save.status == "play" \
                and new_image_path.split("/")[-1][0] != "." \
                and new_image_path.split("/")[-1][0] != "~":
            self.counter = self.counter + 1
            self.log.append(_("Reading new frame..."))
            if self.first == 0:
                self.log.append(_("Reading first frame..."))
                self.first_image, limit, mode = stk.create_first_ref_im(self.work_folder, new_image_path,
                                                                        save_im=save_on)

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
                if align_on:
                    self.log.append(_("Stack and Align New frame..."))
                else:
                    self.log.append(_("Stack New frame..."))

                self.image_ref_save.image, limit, mode = stk.stack_live(self.work_folder, new_image_path,
                                                                        self.counter,
                                                                        ref=self.image_ref_save.image,
                                                                        first_ref=self.first_image,
                                                                        save_im=save_on,
                                                                        align=align_on,
                                                                        stack_methode=stack_methode)

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
            self.log.append(_("New image detected but not considered"))


# ------------------------------------------------------------------------------


class MainWindow(QMainWindow):

    @log
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_stack_window()
        self.ui.setupUi(self)

        self.ui.tFolder.setText(os.path.expanduser(config.get_scan_folder_path()))
        self.ui.tDark.setText(os.path.expanduser(config.get_dark_path()))
        self.ui.tWork.setText(os.path.expanduser(config.get_work_folder_path()))

        self.running = False
        self.counter = 0
        self.align = False
        self.dark = False
        self.pause = False
        self.image_ref_save = ImageRefSave()

        self.setWindowTitle(_("Astro Live Stacker") + f" - v{VERSION}")

        # web stuff
        self.thread = None
        self.web_dir = None

    @log
    def closeEvent(self, event):
        self._stop_www()

        try:
            config.save()
            _logger.info("User configuration saved")
        except OSError as e:
            _logger.error(f"Could not save settings. Error : {e}")
            messaging.error_box("Settings not saved", f"Your settings could not be saved\n\nDetails : {e}")
        super().closeEvent(event)

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
        red.writeto(self.ui.tWork.text() + "/" + "stack_image_" + timestamp + ".fit")
        # red.close()
        del red

    @pyqtSlot(name="on_pb_apply_value_clicked")
    @log
    def cb_apply_value(self):
        work_folder = self.ui.tWork.text()
        if self.counter > 0:
            self.adjust_value(work_folder)
            self.update_image(work_folder, add=False)
        self.ui.log.append(_("Define new display value"))

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
    def update_image(self, work_folder, add=True):
        if add:
            self.counter = self.counter + 1
            self.ui.cnt.setText(str(self.counter))

        # read tiff ( need save_type = "tiff") :
        # pixmap_tiff = QtGui.QPixmap(os.path.expanduser(work_folder + "/" + name_of_tiff_image))

        # read tiff ( need save_type = "jpeg") :
        # pixmap_tiff = QtGui.QPixmap(os.path.expanduser(work_folder + "/" +

        # read image in RAM ( need save_type = "no"):
        qimage_tiff = array2qimage(self.image_ref_save.stack_image, normalize=(2**16-1))
        pixmap_tiff = QPixmap.fromImage(qimage_tiff)

        if pixmap_tiff.isNull():
            self.ui.log.append(_("invalid frame"))

        pixmap_tiff_resize = pixmap_tiff.scaled(self.ui.image_stack.frameGeometry().width(),
                                                self.ui.image_stack.frameGeometry().height(),
                                                Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.ui.image_stack.setPixmap(pixmap_tiff_resize)
        message = _("Updated GUI image")
        self.ui.log.append(_(message))
        _logger.info(message)

    @pyqtSlot(name="on_bBrowseFolder_clicked")
    @log
    def cb_browse_scan(self):
        dir_name = QFileDialog.getExistingDirectory(self, _("Scan folder"), self.ui.tFolder.text())
        if dir_name:
            self.ui.tFolder.setText(dir_name)
            self.ui.pbPlay.setEnabled(True)
            config.set_scan_folder_path(dir_name)

    @pyqtSlot(name="on_bBrowseDark_clicked")
    @log
    def cb_browse_dark(self):
        file_name, _ = QFileDialog.getOpenFileName(self, _("Dark file"), "",
                                                   "Fit Files (*.fit);;All Files (*)")
        if file_name:
            self.ui.tDark.setText(file_name)
            config.set_dark_path(file_name)

    @pyqtSlot(name="on_bBrowseWork_clicked")
    @log
    def cb_browse_work(self):
        dir_name = QFileDialog.getExistingDirectory(self, _("Work folder"), self.ui.tWork.text())
        if dir_name:
            self.ui.tWork.setText(dir_name)
            config.set_work_folder_path(dir_name)

    @pyqtSlot(name="on_pbPlay_clicked")
    @log
    def cb_play(self):
        if self.ui.tFolder.text() != "":

            # check existence of work and scan folders
            work_folder_path = config.get_work_folder_path()
            if not os.path.exists(os.path.expanduser(work_folder_path)) or not os.path.isdir(os.path.expanduser(work_folder_path)):
                self.cb_browse_work()

            scan_folder_path = config.get_scan_folder_path()
            if not os.path.exists(os.path.expanduser(scan_folder_path)) or not os.path.isdir(os.path.expanduser(scan_folder_path)):
                self.cb_browse_scan()

            if self.image_ref_save.status == "stop":
                self.ui.white_slider.setEnabled(False)
                self.ui.black_slider.setEnabled(False)
                self.ui.contrast_slider.setEnabled(False)
                self.ui.brightness_slider.setEnabled(False)
                self.ui.R_slider.setEnabled(False)
                self.ui.G_slider.setEnabled(False)
                self.ui.B_slider.setEnabled(False)
                self.ui.pb_apply_value.setEnabled(False)
                self.ui.bBrowseFolder.setEnabled(False)
                self.ui.bBrowseWork.setEnabled(False)
                self.ui.image_stack.setPixmap(QPixmap(":/icons/dslr-camera.svg"))
                self.counter = 0
                self.ui.cnt.setText(str(self.counter))
                # Print scan folder
                self.ui.log.append(_("Scan folder : ") + os.path.expanduser(self.ui.tFolder.text()))
                # Print work folder
                self.ui.log.append(_("Work folder : ") + os.path.expanduser(self.ui.tWork.text()))

                # check align
                if self.ui.cbAlign.isChecked():
                    self.align = True

                # check dark
                if (self.ui.cbDark.isChecked()) & (self.ui.tDark.text() != ""):
                    self.ui.log.append("Dark : " + os.path.expanduser(self.ui.tDark.text()))
                    self.dark = True

                # Print live method
                if self.align and self.dark:
                    self.ui.log.append(_("Play with alignement type: ") + self.ui.cmMode.currentText() + " and Dark")
                elif self.align:
                    self.ui.log.append(_("Play with alignement type: ") + self.ui.cmMode.currentText())
                else:
                    self.ui.log.append(_("Play with NO alignement"))

                self.file_watcher = WatchOutForFileCreations(os.path.expanduser(self.ui.tFolder.text()),
                                                             os.path.expanduser(self.ui.tWork.text()),
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
                                                             self.dark,
                                                             os.path.expanduser(self.ui.tDark.text()),
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
                    messaging.error_box(title, message)
                    _logger.error(f"{title} : {e}")
                    self.cb_stop()
                    return

                self.file_watcher.start()
                self.file_watcher.print_image.connect(
                    lambda: self.update_image(self.ui.tWork.text(), NAME_OF_TIFF_IMAGE))
            else:
                self.ui.log.append("Play")

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

        else:
            self.ui.log.append(_("No path"))

    @log
    def _setup_work_folder(self):
        work_dir_path = os.path.expanduser(self.ui.tWork.text())
        if os.path.exists(work_dir_path):
            shutil.rmtree(work_dir_path + "/")
        os.mkdir(work_dir_path)
        resources_dir_path = os.path.dirname(os.path.realpath(__file__)) + "/resources_dir"
        shutil.copy(resources_dir_path + "/index.html", work_dir_path)
        shutil.copy(resources_dir_path + "/waiting.jpg", work_dir_path + "/" + NAME_OF_JPEG_IMAGE)

    @pyqtSlot(name="on_pbStop_clicked")
    @log
    def cb_stop(self):
        self.file_watcher.observer.stop()
        self.image_ref_save.status = "stop"
        self.image_ref_save.image = []
        self.image_ref_save.stack_image = []
        self.ui.bBrowseFolder.setEnabled(True)
        self.ui.bBrowseWork.setEnabled(True)
        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        self.ui.pbReset.setEnabled(True)
        self.ui.pbPause.setEnabled(False)
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
    @log
    def _start_www(self):
        self.web_dir = os.path.join(os.path.dirname(__file__),
                                    os.path.expanduser(config.get_work_folder_path()))
        ip_address = MainWindow.get_ip()
        port_number = config.get_www_server_port_number()
        try:
            self.thread = StoppableServerThread(self.web_dir)
            self.thread.start()

            # Server is now started and listens on specified port on *all* available interfaces.
            # We get the machine ip address and warn user if detected ip is loopback (127.0.0.1)
            # since in this case, the image server won't be reachable by any other machine
            if "127.0.0.1" == ip_address:
                log_function = _logger.warning
                title = "Image server access is limited"
                message = "Image server IP address is 127.0.0.1.\n\nImage server won't be reachable by other " \
                          "machines. Please check your network connection"
                messaging.warning_box(title, message)
            else:
                log_function = _logger.info

            log_function(f"Image  server started. http://{ip_address}:{port_number}")
        except PermissionError:
            title = "Could not start image server"
            message = f"The image server needs to listen on port n°{port_number} but this port is already in use.\n\n"
            message += "Quit ALS then add or modify the 'www_server_port' entry in your config file " \
                       "(located at ~/.als.cfg) to specify another port number"
            _logger.error(title)
            messaging.error_box(title, message)
            self._stop_www()
            self.ui.cbWww.setChecked(False)

    @log
    def _stop_www(self):
        if self.thread:
            self.thread.stop()
            self.thread.join()
            self.thread = None
            _logger.info("Web server stopped")

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
        messaging.error_box("Config file is invalid", str(e))
        print(f"***** ERROR : user config file is invalid : {e}")
        sys.exit(1)

    _logger.info(f"Starting Astro Live Stacker v{VERSION} in {os.path.dirname(os.path.realpath(__file__))}")
    window = MainWindow()
    _logger.debug("Building and showing main window")
    window.show()
    app_return_code = app.exec()
    _logger.info(f"Astro Live Stacker terminated with return code = {app_return_code}")
    sys.exit(app_return_code)
