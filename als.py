#!/usr/bin/python3
# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets
from PyQt5 import QtCore
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


import alsui  # import du fichier alsui.py généré par : pyuic5 alsui.ui -x -o alsui.py

# ------------------------------------------------------------------------------
class WatchOutForFileCreations(QtCore.QThread):
    def __init__(self, path, filename):
        super(WatchOutForFileCreations, self).__init__()
        self.path = path
        self.filename = filename
        self.observer = Observer()
        self.event_handler = MyEventHandler(self.filename)
        self.observer.schedule(self.event_handler, self.path, recursive=False)
        self.observer.start()
        self.connect(self.event_handler, QtCore.SIGNAL("fileCreated"), self.modified)

    def run(self):
        pass

    def created(self):
        self.emit(QtCore.SIGNAL("fileCreated1"))


# ------------------------------------------------------------------------------


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.ui = alsui.Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.ui.pbPlay.clicked.connect(self.cb_play)
        self.ui.pbStop.clicked.connect(self.cb_stop)
        self.ui.pbReset.clicked.connect(self.cb_reset)   
                     
        self.ui.bBrowseFolder.clicked.connect(self.cb_browse_folder)                
        self.ui.bBrowseDark.clicked.connect(self.cb_browse_dark)                
        
        self.running = False
        
        self.counter=0

                     
# ------------------------------------------------------------------------------
# Callbacks
    def cb_browse_folder(self):
        DirName = QtWidgets.QFileDialog.getExistingDirectory(self,"Répertoire à scanner",self.ui.tFolder.text())
        if DirName:
            self.ui.tFolder.setText(DirName)
    
    def cb_browse_dark(self):
        fileName,_ = QtWidgets.QFileDialog.getOpenFileName(self,"Fichier de Dark", "","Fit Files (*.fit);;All Files (*)")
        if fileName:
            self.ui.tDark.setText(fileName)
 
    def cb_play(self):
        # recuperation des parametres
        self.ui.log.append("Play")

        if len(self.ui.tFolder.text())==0 :
            print( "Dossier a scanner: <./>")
        else: 
            print( "Dossier a scanner: <" + self.ui.tFolder.text() +">")
        if self.ui.cbAlign.isChecked():
            print( "Alignement"  )        
        if (self.ui.cbDark.isChecked())&(len(self.ui.tDark.text())!=0):
            print( "Dark : <" + self.ui.tDark.text()  +">")   
                         
        self.running = True
        self.ui.pbPlay.setEnabled(False)
        self.ui.pbStop.setEnabled(True)
        self.counter=0

        # Lancement du watchdog
           
    def cb_stop(self):
        self.running = False
        self.ui.pbStop.setEnabled(False)
        self.ui.pbPlay.setEnabled(True)
        observer.stop()
        self.counter=0
        self.ui.progressBar.setValue(self.counter)
                    
    def cb_reset(self):
        self.counter=0
                     


# ------------------------------------------------------------------------------
import sys
app = QtWidgets.QApplication(sys.argv)
window = MyWindow()
window.show()

sys.exit(app.exec_())
