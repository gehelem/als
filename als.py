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

# !/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from datetime import datetime
import shutil
import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from alsui import Ui_stack_window  # import du fichier alsui.py généré par : pyuic5 alsui.ui -x -o alsui.py
from astropy.io import fits

# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import stack as stk

name_of_tiff_image = "stack_image.tiff"
name_of_fit_image = "stack_ref_image.fit"


# class ColorParam:
#    def __init__(self):
#        self.contrast = 1
#        self.brightness = 0
#        self.black = 0
#        self.white = 65535


class MyEventHandler(FileSystemEventHandler, QtCore.QThread):
    created_signal = QtCore.pyqtSignal()
    new_image_path = ""

    def __init__(self):
        super(MyEventHandler, self).__init__()

    def on_created(self, event):
        # if not event.is_directory:
        if event.event_type == 'created':
            print("New image arrive: %s" % event.src_path)
            self.new_image_path = event.src_path
            self.created_signal.emit()


# ------------------------------------------------------------------------------


class WatchOutForFileCreations(QtCore.QThread):
    print_image = QtCore.pyqtSignal()

    def __init__(self, path, work_folder, align_on, save_on, stack_methode,
                 log, white_slider, black_slider, contrast_slider, brightness_slider,
                 R_slider, G_slider, B_slider, apply_button):
        super(WatchOutForFileCreations, self).__init__()
        self.white_slider = white_slider
        self.black_slider = black_slider
        self.contrast_slider = contrast_slider
        self.brightness_slider = brightness_slider
        self.R_slider = R_slider
        self.G_slider = G_slider
        self.B_slider = B_slider
        self.apply_button = apply_button
        self.log = log
        self.path = path
        self.work_folder = work_folder
        self.first = 0
        self.counter = 0
        print(self.work_folder)
        print(self.path)
        self.observer = Observer()
        self.event_handler = MyEventHandler()
        self.observer.schedule(self.event_handler, self.path, recursive=False)
        self.observer.start()
        self.event_handler.created_signal.connect(lambda: self.created(self.event_handler.new_image_path,
                                                                       align_on, save_on, stack_methode))

    def run(self):
        pass

    def created(self, new_image_path, align_on, save_on, stack_methode):
        self.counter = self.counter + 1
        if self.first == 0:
            limit, mode = stk.create_first_ref_im(self.work_folder, new_image_path, name_of_fit_image, save_im=save_on,
                                                  param=[self.contrast_slider.value() / 10.,
                                                         self.brightness_slider.value(),
                                                         self.black_slider.value(),
                                                         self.white_slider.value(),
                                                         self.R_slider.value() / 100.,
                                                         self.G_slider.value() / 100.,
                                                         self.B_slider.value() / 100.
                                                         ])
            self.log.append("first file created : %s" % self.work_folder + "/" + name_of_fit_image)
            self.first = 1
            self.white_slider.setMaximum(np.int(limit))
            self.brightness_slider.setMaximum(np.int(limit) / 2.)
            self.brightness_slider.setMinimum(np.int(-1*limit) / 2.)
            if self.white_slider.value() > limit:
                self.white_slider.setSliderPosition(limit)
            elif self.white_slider.value() < -1*limit:
                self.white_slider.setSliderPosition(-1*limit)
            self.black_slider.setMaximum(np.int(limit))
            if self.black_slider.value() > limit:
                self.black_slider.setSliderPosition(limit)
            if self.brightness_slider.value() > limit / 2.:
                self.brightness_slider.setSliderPosition(limit / 2.)
            if limit == 2. ** 16 - 1:
                self.log.append("Read 16bit image ...")
            elif limit == 2. ** 8 - 1:
                self.log.append("Read 8bit image ...")
            self.white_slider.setEnabled(True)
            self.black_slider.setEnabled(True)
            self.contrast_slider.setEnabled(True)
            self.brightness_slider.setEnabled(True)
            self.apply_button.setEnabled(True)

            if mode == "rgb":
                # activation des barre r, g, b
                self.log.append("Read RGB image ...")
                self.R_slider.setEnabled(True)
                self.G_slider.setEnabled(True)
                self.B_slider.setEnabled(True)
            elif mode == "gray":
                # desactivation des barre r, g, b
                self.log.append("Read B&W image ...")
                self.R_slider.setEnabled(False)
                self.G_slider.setEnabled(False)
                self.B_slider.setEnabled(False)

        else:
            # appelle de la fonction stack live
            stk.stack_live(self.work_folder, new_image_path, name_of_fit_image, self.counter,
                           save_im=save_on, align=align_on, stack_methode=stack_methode,
                           param=[self.contrast_slider.value() / 10.,
                                  self.brightness_slider.value(),
                                  self.black_slider.value(),
                                  self.white_slider.value(),
                                  self.R_slider.value() / 100.,
                                  self.G_slider.value() / 100.,
                                  self.B_slider.value() / 100.
                                  ])
            self.log.append("file created : %s" % self.work_folder + "/" + name_of_fit_image)
        self.print_image.emit()


# ------------------------------------------------------------------------------


class als_main_window(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(als_main_window, self).__init__(parent)
        self.ui = Ui_stack_window()
        self.ui.setupUi(self)

        self.connect_actions()
        self.running = False
        self.counter = 0
        self.align = False
        self.dark = False
        self.pause = False

    def connect_actions(self):

        self.ui.pbPlay.clicked.connect(self.cb_play)
        self.ui.pbStop.clicked.connect(self.cb_stop)
        self.ui.pbReset.clicked.connect(self.cb_reset)
        self.ui.pbSave.clicked.connect(self.cb_save)
        self.ui.bBrowseFolder.clicked.connect(self.cb_browse_folder)
        self.ui.bBrowseDark.clicked.connect(self.cb_browse_dark)
        self.ui.bBrowseWork.clicked.connect(self.cb_browse_work)
        self.ui.pb_apply_value.clicked.connect(lambda: self.apply_value(self.counter, self.ui.tWork.text()))
        # need add event for pause button and add pause button

        # update slider
        self.ui.contrast_slider.valueChanged['int'].connect(
            lambda: self.ui.contrast.setNum(self.ui.contrast_slider.value() / 10))
        self.ui.brightness_slider.valueChanged['int'].connect(self.ui.brightness.setNum)
        self.ui.black_slider.valueChanged['int'].connect(self.ui.black.setNum)
        self.ui.white_slider.valueChanged['int'].connect(self.ui.white.setNum)
        self.ui.R_slider.valueChanged['int'].connect(lambda: self.ui.R_value.setNum(self.ui.R_slider.value() / 100.))
        self.ui.G_slider.valueChanged['int'].connect(lambda: self.ui.G_value.setNum(self.ui.G_slider.value() / 100.))
        self.ui.B_slider.valueChanged['int'].connect(lambda: self.ui.B_value.setNum(self.ui.B_slider.value() / 100.))

    # ------------------------------------------------------------------------------
    # Callbacks
    def cb_save(self):
        timestamp = str(datetime.fromtimestamp(datetime.timestamp(datetime.now())))
        self.ui.log.append("Saving : stack-" + timestamp + ".fit")
        shutil.copy(os.path.expanduser(self.ui.tWork.text()) + "/" + name_of_fit_image,
                    os.path.expanduser(self.ui.tWork.text()) + "/stack-" + timestamp + ".fit")

    def apply_value(self, counter, work_folder):
        if counter > 0:
            new_tiff_image = self.ajuste_value(work_folder)
            self.update_image(work_folder, new_tiff_image, add=False)
        self.ui.log.append("Define new display value")

    def ajuste_value(self, work_folder):
        # open ref image
        image_fit = fits.open(os.path.expanduser(work_folder + "/" + name_of_fit_image))
        image = image_fit[0].data
        image_fit.close()

        # test rgb or gray
        if len(image.shape) == 2:
            mode = "gray"
        elif len(image.shape) == 3:
            mode = "rgb"
        else:
            raise ValueError("fit format not support")
        # apply cv2 transformation in rgb image
        if mode == "rgb":
            image = np.rollaxis(image, 0, 3)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        else:
            image = image
        # test type image
        limit, im_type = stk.test_utype(image)

        # apply value transformation
        image = np.float32(image)

        print("correct display image")
        print("contrast value : %s" % str(self.ui.contrast_slider.value() / 10.))
        print("brightness value : %s" % str(self.ui.brightness_slider.value()))
        print("pente : %f" % (1. / ((self.ui.white_slider.value() - self.ui.black_slider.value()) / limit)))

        if (self.ui.R_slider.value() / 100.) != 1 or \
                (self.ui.G_slider.value() / 100.) != 1 or \
                (self.ui.B_slider.value() / 100.) != 1:
            if mode == "rgb":
                print("R contrast value : %s" % str(self.ui.R_slider.value() / 100.))
                print("G contrast value : %s" % str(self.ui.G_slider.value() / 100.))
                print("B contrast value : %s" % str(self.ui.B_slider.value() / 100.))
                image[:, :, 0] = image[:, :, 0] * (self.ui.B_slider.value() / 100.)
                image[:, :, 1] = image[:, :, 1] * (self.ui.G_slider.value() / 100.)
                image[:, :, 2] = image[:, :, 2] * (self.ui.R_slider.value() / 100.)
        if self.ui.black_slider.value() != 0 or self.ui.white_slider.value() != limit:
            image = np.where(image < self.ui.white_slider.value(), image, self.ui.white_slider.value())
            image = np.where(image > self.ui.black_slider.value(), image, self.ui.black_slider.value())
            image = image * (1. / ((self.ui.white_slider.value() - self.ui.black_slider.value()) / limit))

        image = image * (self.ui.contrast_slider.value() / 10.) + self.ui.brightness_slider.value()
        image = np.where(image < limit, image, limit)
        image = np.where(image > 0, image, 0)
        if im_type == "uint16":
            image = np.uint16(image)
        elif im_type == "uint8":
            image = np.uint8(image)

        # write tiff file
        # cv2.imshow("image", image/65535.)
        cv2.imwrite(os.path.expanduser(work_folder + "/" + name_of_tiff_image), image)
        self.ui.log.append("Adjusted GUI image")
        return name_of_tiff_image

    def update_image(self, work_folder, tiff_image, add=True):
        if add:
            self.counter = self.counter + 1
            self.ui.cnt.setText(str(self.counter))

        pixmap_tiff = QtGui.QPixmap(os.path.expanduser(work_folder + "/" + tiff_image))

        if pixmap_tiff.isNull():
            self.ui.log.append("Image non valide !")

        pixmap_tiff_resize = pixmap_tiff.scaled(self.ui.image_stack.frameGeometry().width(),
                                                self.ui.image_stack.frameGeometry().height(),
                                                QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.ui.image_stack.setPixmap(pixmap_tiff_resize)
        self.ui.log.append("Updated GUI image")

    def cb_browse_folder(self):
        DirName = QtWidgets.QFileDialog.getExistingDirectory(self, "Répertoire à scanner", self.ui.tFolder.text())
        if DirName:
            self.ui.tFolder.setText(DirName)
            self.ui.pbPlay.setEnabled(True)

    def cb_browse_dark(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Fichier de Dark", "",
                                                            "Fit Files (*.fit);;All Files (*)")
        if fileName:
            self.ui.tDark.setText(fileName)

    def cb_browse_work(self):
        DirName = QtWidgets.QFileDialog.getExistingDirectory(self, "Répertoire de travail", self.ui.tWork.text())
        if DirName:
            self.ui.tWork.setText(DirName)

    def cb_play(self):

        if self.ui.tFolder.text() != "":

            self.ui.white_slider.setEnabled(False)
            self.ui.black_slider.setEnabled(False)
            self.ui.contrast_slider.setEnabled(False)
            self.ui.brightness_slider.setEnabled(False)
            self.ui.R_slider.setEnabled(False)
            self.ui.G_slider.setEnabled(False)
            self.ui.B_slider.setEnabled(False)
            self.ui.pb_apply_value.setEnabled(False)
            self.ui.image_stack.setPixmap(QtGui.QPixmap("dslr-camera.svg"))
            self.counter = 0
            self.ui.cnt.setText(str(self.counter))

            if self.pause:
                self.fileWatcher.observer.start()
                self.pause = False
                # desactivate play button
                self.ui.pbPlay.setEnabled(False)
                # activate stop button
                self.ui.pbStop.setEnabled(True)
            else:
                # Print scan folder
                self.ui.log.append("Dossier a scanner : " + os.path.expanduser(self.ui.tFolder.text()))
                # Print work folder
                self.ui.log.append("Dossier de travail : " + os.path.expanduser(self.ui.tWork.text()))

                # check align
                if self.ui.cbAlign.isChecked():
                    self.align = True

                # check dark
                if (self.ui.cbDark.isChecked()) & (self.ui.tDark.text() != ""):
                    self.ui.log.append("Dark : " + os.path.expanduser(self.ui.tDark.text()))
                    self.dark = True

                # Print live method
                if self.align and self.dark:
                    self.ui.log.append("Play with alignement type: " + self.ui.cmMode.currentText() + " and Dark")
                elif self.align:
                    self.ui.log.append("Play with alignement type: " + self.ui.cmMode.currentText())
                else:
                    self.ui.log.append("Play with NO alignement")

                # Lancement du watchdog
                self.fileWatcher = WatchOutForFileCreations(os.path.expanduser(self.ui.tFolder.text()),
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
                                                            self.ui.pb_apply_value
                                                            )

                if os.path.exists(os.path.expanduser(self.ui.tWork.text())):
                    shutil.rmtree(os.path.expanduser(self.ui.tWork.text()) + "/")
                    os.mkdir(os.path.expanduser(self.ui.tWork.text()))
                else:
                    os.mkdir(os.path.expanduser(self.ui.tWork.text()))

                self.fileWatcher.start()
                self.running = True

                # desactivate play button
                self.ui.pbPlay.setEnabled(False)
                self.ui.pbReset.setEnabled(False)
                # activate stop button
                self.ui.pbStop.setEnabled(True)

                self.fileWatcher.print_image.connect(
                    lambda: self.update_image(self.ui.tWork.text(), name_of_tiff_image))

        else:
            self.ui.log.append("No have path")

    def cb_stop(self):
        self.fileWatcher.observer.stop()
        self.running = False
        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        self.ui.pbReset.setEnabled(True)
        self.ui.log.append("Stop")

    def cb_pause(self):
        self.fileWatcher.observer.stop()
        self.running = False
        self.pause = True
        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        self.ui.pbReset.setEnabled(True)
        self.ui.log.append("Stop")

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
        self.ui.image_stack.setPixmap(QtGui.QPixmap("dslr-camera.svg"))
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

    def main(self):
        self.show()


# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = als_main_window()
    window.main()
    sys.exit(app.exec_())
