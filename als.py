#!/usr/bin/python3
# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets
from PyQt5 import QtCore
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from alsui import Ui_stack_window  # import du fichier alsui.py généré par : pyuic5 alsui.ui -x -o alsui.py

# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import stack as stk


class MyEventHandler(FileSystemEventHandler, QtCore.QThread):
    created_signal = QtCore.pyqtSignal()
    new_image_path = ""

    def __init__(self):
        super(MyEventHandler, self).__init__()

    def on_created(self, event):
        if not event.is_directory:
            print("New image arrive: %s" % event.src_path)
            self.new_image_path = event.src_path
            self.created_signal.emit()


# ------------------------------------------------------------------------------

class WatchOutForFileCreations(QtCore.QThread):
    def __init__(self, path, work_folder, first_image):
        super(WatchOutForFileCreations, self).__init__()
        self.path = path
        self.work_folder = work_folder
        self.first_image = first_image
        self.observer = Observer()
        self.event_handler = MyEventHandler()
        self.observer.schedule(self.event_handler, self.path, recursive=False)
        self.observer.start()
        # self.connect(self.event_handler, QtCore.SIGNAL("fileCreated"), self.modified)
        self.event_handler.created_signal.connect(self.created(self.event_handler.new_image_path))
        stk.create_first_ref_im(self.work_folder, self.first_image, "stack_ref_image.fit")

    def run(self):
        pass

    def created(self, new_image_path):
        # appelle de la fonction stack live
        # stk.stack_live(self.work_folder, new_image_path, "stack_ref_image.fit", mode="rgb", save_im=True)
        print("file created : %s" % new_image_path)


# ------------------------------------------------------------------------------


class als_main_window(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(als_main_window, self).__init__(parent)
        self.ui = Ui_stack_window()
        self.ui.setupUi(self)

        self.connect_actions()
        self.running = False
        self.counter = 0

    def connect_actions(self):

        self.ui.pbPlay.clicked.connect(self.cb_play)
        self.ui.pbStop.clicked.connect(self.cb_stop)
        self.ui.pbReset.clicked.connect(self.cb_reset)
        self.ui.bBrowseFolder.clicked.connect(self.cb_browse_folder)
        self.ui.bBrowseDark.clicked.connect(self.cb_browse_dark)

    # ------------------------------------------------------------------------------
    # Callbacks
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

    def cb_play(self):
        if self.ui.tFolder.text() != "":

            # Print scan folder
            self.ui.log.append("Dossier a scanner: <" + self.ui.tFolder.text() + ">")

            # check align
            if self.ui.cbAlign.isChecked():
                self.align = True

            # check dark
            if (self.ui.cbDark.isChecked()) & (self.ui.tDark.text() != ""):
                self.ui.log.append("Dark : <" + self.ui.tDark.text() + ">")
                self.dark = True

            # Lancement du watchdog

            # /!\ besoin de créer 2 nouvelle zone, un pour le dossier de travail et un pour pointer la première image
            self.fileWatcher = WatchOutForFileCreations(self.ui.tFolder.text(), work_folder, first_image)
            self.fileWatcher.start()

            # Print live method
            if self.align and self.dark:
                self.ui.log.append("Play with alignement and Dark")
            elif self.align:
                self.ui.log.append("Play with alignement")
            else:
                self.ui.log.append("Play")

            self.running = True

            # desactivate play button
            self.ui.pbPlay.setEnabled(False)
            # activate stop button
            self.ui.pbStop.setEnabled(True)
            self.counter = 0
        else:
            self.ui.log.append("No have path")

    def cb_stop(self):
        self.running = False
        # /!\ impossible d'arreter le watchdog

        # self.fileWatcher.stop()
        # Observer.stop(self.fileWatcher)
        self.counter = 0
        self.ui.progressBar.setValue(self.counter)

        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        self.ui.log.append("Stop")

    def cb_reset(self):
        self.counter = 0

    def main(self):
        self.show()


# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = als_main_window()
    window.main()
    sys.exit(app.exec_())
