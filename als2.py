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
import gettext
import shutil
import configparser

import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from alsui2 import Ui_AlsWindow  # import du fichier alsui.py généré par : pyuic5 alsui.ui -x -o alsui.py
from astropy.io import fits

import stack2


# internationalization :
# Generate .pot file :
# pygettext -o als.pot als.py
# open als/locale/xx/LC_MESSAGES/als.po with poedit and update with pot file

gettext.install('als', 'locale')
config = configparser.ConfigParser()


class MyEventHandler(FileSystemEventHandler, QtCore.QThread):
    created_signal = QtCore.pyqtSignal()
    new_image_path = ""

    def __init__(self):
        super(MyEventHandler, self).__init__()

    def on_created(self, event):
        # if not event.is_directory:
        if event.event_type == 'created':
            self.new_image_path = event.src_path
            self.created_signal.emit()

class WatchOutForFileCreations(QtCore.QThread):
    print_image = QtCore.pyqtSignal()

    def __init__(self, folderscan,log):

        super(WatchOutForFileCreations, self).__init__()
        self.folderscan = folderscan
        self.observer = Observer()
        self.event_handler = MyEventHandler()
        self.observer.schedule(self.event_handler, self.folderscan, recursive=False)
        self.observer.start()
        self.log=log
        self.counter=0

        self.event_handler.created_signal.connect(lambda: self.created(self.event_handler.new_image_path,log,counter))

    def created(self, new_image_path,log,counter):
        self.log.append(_("Incoming") + " " + new_image_path)

        # test image format ".fit" or ".fits" or other
        if new_image_path.rfind(".fit") != -1:
            if new_image_path[new_image_path.rfind(".fit"):] == ".fit":
                extension = ".fit"
            elif new_image_path[new_image_path.rfind(".fit"):] == ".fits":
                extension = ".fits"
            raw_im = False
        else:
            # Other format = raw camera format (cr2, ...)
            extension = new_image_path[new_image_path.rfind("."):]
            raw_im = True

        if not raw_im:
            # open ref fit image
            new_fit = fits.open(new_image_path)
            new = new_fit[0].data
            # save fit header
            new_header = new_fit[0].header
            new_fit.close()
            # test image type
            im_limit, im_type = stack2.test_utype(new,log)
            # test rgb or gray or no debayer
            new, im_mode = stack2.test_and_debayer_to_rgb(new_header, new,log)
        else:
            self.log.append(_("Convert DSLR frame"))
            # convert camera raw to numpy array
            new = rawpy.imread(im_path).postprocess(gamma=(1, 1), no_auto_bright=True, output_bps=16)
            im_mode = "rgb"
            extension = ".fits"
            im_limit = 2. ** 16 - 1
            # convert cv2 order to classic order
            new = np.rollaxis(new, 2, 0)

class als_main_window(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(als_main_window, self).__init__(parent)
        self.ui = Ui_AlsWindow()
        self.ui.setupUi(self)

        self.load_config()
        self.translate_labels()
        self.connect_actions()

    def closeEvent(self, event):
        config.write(open('./als.ini', 'w'))
        super(als_main_window, self).closeEvent(event)

    def load_config(self):
        config.read('./als.ini')
        self.folderscan=os.path.expanduser(config['Default']['folderscan'])
        self.folderwork=os.path.expanduser(config['Default']['folderwork'])
        self.filedark=os.path.expanduser(config['Default']['filedark'])
        self.ui.fScan.setText(self.folderscan)
        self.ui.fWork.setText(self.folderwork)
        self.ui.fDark.setText(self.filedark)

    def translate_labels(self):
        self.setWindowTitle(_("Astro Live Stacker"))

        self.ui.pbPlay.setText(_("Play"))
        self.ui.pbPause.setText(_("Pause"))
        self.ui.pbStop.setText(_("Stop"))
        self.ui.pbScan.setText(_("Scan folder") + " :")
        self.ui.pbDark.setText(_("Dark file") + " :")
        self.ui.pbWork.setText(_("Work folder") + " :")
        self.ui.cDark.setText(_("Apply dark"))
        self.ui.cKeepframes.setText(_("Keep all frames"))
        self.ui.cEnablewww.setText(_("Enable webserver"))
        self.ui.cAlign.setText(_("Register"))
        self.ui.pbSave.setText(_("Save frame"))

    def connect_actions(self):
        self.ui.pbPlay.clicked.connect(self.cb_play)
        self.ui.pbPause.clicked.connect(self.cb_pause)
        self.ui.pbStop.clicked.connect(self.cb_stop)

    def cb_play(self):
        self.ui.pbPlay.setEnabled(False)
        self.ui.pbPause.setEnabled(True)
        self.ui.pbStop.setEnabled(True)
        self.ui.tbLog.append(_("Play") + "--------------------")
        self.ui.tbLog.append(_("Scan folder") + self.folderscan)

        self.fileWatcher = WatchOutForFileCreations(self.folderscan,self.ui.tbLog)

    def cb_pause(self):
        self.fileWatcher.observer.stop()
        self.ui.pbPlay.setEnabled(True)
        self.ui.pbPause.setEnabled(False)
        self.ui.pbStop.setEnabled(True)
        self.ui.tbLog.append(_("Pause") + "--------------------")

    def cb_stop(self):
        self.fileWatcher.observer.stop()
        self.ui.pbPlay.setEnabled(True)
        self.ui.pbPause.setEnabled(False)
        self.ui.pbStop.setEnabled(False)
        self.ui.tbLog.append(_("Stop") + "--------------------")

    def main(self):
        self.show()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    window = als_main_window()
    window.main()
    sys.exit(app.exec_())
