#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from PyQt5 import QtCore, QtGui, QtWidgets
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
        # if not event.is_directory:
        if event.event_type == 'created':
            print("New image arrive: %s" % event.src_path)
            self.new_image_path = event.src_path
            self.created_signal.emit()


# ------------------------------------------------------------------------------


class WatchOutForFileCreations(QtCore.QThread):
    print_image = QtCore.pyqtSignal()

    def __init__(self, path, work_folder):
        super(WatchOutForFileCreations, self).__init__()
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
        self.event_handler.created_signal.connect(lambda: self.created(self.event_handler.new_image_path))

    def run(self):
        pass

    def created(self, new_image_path):
        if self.first == 0:
            stk.create_first_ref_im(self.work_folder, new_image_path, "stack_ref_image.fit")
            print("first file created : %s" % self.work_folder + "/stack_ref_image.fit")
            self.first = 1
        else:
            # appelle de la fonction stack live
            stk.stack_live(self.work_folder, new_image_path, "stack_ref_image.fit", self.counter,
                           save_im=False, align=True, stack_methode="Sum")
            print("file created : %s" % self.work_folder + "/stack_ref_image.fit")
        self.print_image.emit()
        self.counter = self.counter + 1


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

    def connect_actions(self):

        self.ui.pbPlay.clicked.connect(self.cb_play)
        self.ui.pbStop.clicked.connect(self.cb_stop)
        self.ui.pbReset.clicked.connect(self.cb_reset)
        self.ui.bBrowseFolder.clicked.connect(self.cb_browse_folder)
        self.ui.bBrowseDark.clicked.connect(self.cb_browse_dark)
        self.ui.bBrowseWork.clicked.connect(self.cb_browse_work)

    # ------------------------------------------------------------------------------
    # Callbacks
    def update_image(self):
        effect = QtWidgets.QGraphicsColorizeEffect(self.ui.image_stack)
        effect.setStrength(0.0)
        self.ui.image_stack.setGraphicsEffect(effect)
        pixmap_tiff = QtGui.QPixmap(os.path.expanduser(self.ui.tWork.text() + "/" + "stack_image.tiff"))
        if pixmap_tiff.isNull():
            print("Image non valide !")
        pixmap_tiff_resize = pixmap_tiff.scaled(self.ui.image_stack.frameGeometry().width(),
                                                self.ui.image_stack.frameGeometry().height(),
                                                QtCore.Qt.KeepAspectRatio)
        self.ui.image_stack.setPixmap(pixmap_tiff_resize)

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

            # Lancement du watchdog

            self.fileWatcher = WatchOutForFileCreations(os.path.expanduser(self.ui.tFolder.text()),
                                                        os.path.expanduser(self.ui.tWork.text()))
            self.fileWatcher.start()
            # self.ui.cnt.text=0
            # os.remove(os.path.expanduser(self.ui.tWork.text())+"/*")

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
            self.fileWatcher.print_image.connect(lambda: self.update_image())
        else:
            self.ui.log.append("No have path")

    def cb_stop(self):
        self.fileWatcher.observer.stop()
        self.running = False
        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        self.ui.log.append("Stop")

    def cb_reset(self):
        self.ui.log.append("Reset")

    def main(self):
        self.show()


# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = als_main_window()
    window.main()
    sys.exit(app.exec_())
