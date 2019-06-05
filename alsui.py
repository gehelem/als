# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './alsui.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_stack_window(object):
    def setupUi(self, stack_window):
        stack_window.setObjectName("stack_window")
        stack_window.resize(806, 851)
        stack_window.setMinimumSize(QtCore.QSize(0, 700))
        self.centralwidget = QtWidgets.QWidget(stack_window)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.gridLayout.setObjectName("gridLayout")
        self.cbKeep = QtWidgets.QCheckBox(self.centralwidget)
        self.cbKeep.setMaximumSize(QtCore.QSize(16777215, 20))
        self.cbKeep.setObjectName("cbKeep")
        self.gridLayout.addWidget(self.cbKeep, 4, 2, 1, 1)
        self.bBrowseWork = QtWidgets.QPushButton(self.centralwidget)
        self.bBrowseWork.setMaximumSize(QtCore.QSize(80, 40))
        self.bBrowseWork.setObjectName("bBrowseWork")
        self.gridLayout.addWidget(self.bBrowseWork, 3, 0, 1, 1)
        self.cbAlign = QtWidgets.QCheckBox(self.centralwidget)
        self.cbAlign.setMaximumSize(QtCore.QSize(150, 20))
        self.cbAlign.setChecked(True)
        self.cbAlign.setObjectName("cbAlign")
        self.gridLayout.addWidget(self.cbAlign, 0, 2, 1, 1)
        self.cmMode = QtWidgets.QComboBox(self.centralwidget)
        self.cmMode.setMaximumSize(QtCore.QSize(16777215, 30))
        self.cmMode.setObjectName("cmMode")
        self.cmMode.addItem("")
        self.cmMode.addItem("")
        self.gridLayout.addWidget(self.cmMode, 3, 2, 1, 1)
        self.bBrowseDark = QtWidgets.QPushButton(self.centralwidget)
        self.bBrowseDark.setEnabled(False)
        self.bBrowseDark.setMaximumSize(QtCore.QSize(80, 40))
        self.bBrowseDark.setObjectName("bBrowseDark")
        self.gridLayout.addWidget(self.bBrowseDark, 1, 0, 1, 1)
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.label_10 = QtWidgets.QLabel(self.centralwidget)
        self.label_10.setObjectName("label_10")
        self.horizontalLayout_11.addWidget(self.label_10)
        self.tempo_value = QtWidgets.QSpinBox(self.centralwidget)
        self.tempo_value.setMinimumSize(QtCore.QSize(50, 0))
        self.tempo_value.setMaximumSize(QtCore.QSize(16777215, 30))
        self.tempo_value.setMaximum(60)
        self.tempo_value.setProperty("value", 0)
        self.tempo_value.setObjectName("tempo_value")
        self.horizontalLayout_11.addWidget(self.tempo_value)
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_11.addWidget(self.label_4)
        self.gridLayout.addLayout(self.horizontalLayout_11, 5, 2, 1, 1)
        self.tScan = QtWidgets.QLineEdit(self.centralwidget)
        self.tScan.setEnabled(False)
        self.tScan.setMaximumSize(QtCore.QSize(16777215, 30))
        self.tScan.setObjectName("tScan")
        self.gridLayout.addWidget(self.tScan, 0, 1, 1, 1)
        self.tDark = QtWidgets.QLineEdit(self.centralwidget)
        self.tDark.setEnabled(False)
        self.tDark.setMaximumSize(QtCore.QSize(16777215, 30))
        self.tDark.setObjectName("tDark")
        self.gridLayout.addWidget(self.tDark, 1, 1, 1, 1)
        self.cnt = QtWidgets.QLabel(self.centralwidget)
        self.cnt.setMaximumSize(QtCore.QSize(16777215, 30))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.cnt.setFont(font)
        self.cnt.setAlignment(QtCore.Qt.AlignCenter)
        self.cnt.setObjectName("cnt")
        self.gridLayout.addWidget(self.cnt, 4, 1, 1, 1)
        self.bBrowseFolder = QtWidgets.QPushButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bBrowseFolder.sizePolicy().hasHeightForWidth())
        self.bBrowseFolder.setSizePolicy(sizePolicy)
        self.bBrowseFolder.setMinimumSize(QtCore.QSize(20, 0))
        self.bBrowseFolder.setMaximumSize(QtCore.QSize(80, 40))
        self.bBrowseFolder.setObjectName("bBrowseFolder")
        self.gridLayout.addWidget(self.bBrowseFolder, 0, 0, 1, 1)
        self.cbWww = QtWidgets.QCheckBox(self.centralwidget)
        self.cbWww.setMaximumSize(QtCore.QSize(16777215, 20))
        self.cbWww.setObjectName("cbWww")
        self.gridLayout.addWidget(self.cbWww, 4, 0, 1, 1)
        self.tWork = QtWidgets.QLineEdit(self.centralwidget)
        self.tWork.setEnabled(False)
        self.tWork.setMaximumSize(QtCore.QSize(16777215, 30))
        self.tWork.setObjectName("tWork")
        self.gridLayout.addWidget(self.tWork, 3, 1, 1, 1)
        self.cbDark = QtWidgets.QCheckBox(self.centralwidget)
        self.cbDark.setMaximumSize(QtCore.QSize(150, 20))
        self.cbDark.setObjectName("cbDark")
        self.gridLayout.addWidget(self.cbDark, 1, 2, 1, 1)
        self.pbPlay = QtWidgets.QPushButton(self.centralwidget)
        self.pbPlay.setMaximumSize(QtCore.QSize(16777215, 30))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.pbPlay.setFont(font)
        self.pbPlay.setStyleSheet("background-color: rgb(138, 226, 52)")
        self.pbPlay.setObjectName("pbPlay")
        self.gridLayout.addWidget(self.pbPlay, 0, 3, 1, 1)
        self.pbSave = QtWidgets.QPushButton(self.centralwidget)
        self.pbSave.setMaximumSize(QtCore.QSize(16777215, 30))
        self.pbSave.setObjectName("pbSave")
        self.gridLayout.addWidget(self.pbSave, 5, 3, 1, 1)
        self.pbReset = QtWidgets.QPushButton(self.centralwidget)
        self.pbReset.setMaximumSize(QtCore.QSize(16777215, 30))
        self.pbReset.setObjectName("pbReset")
        self.gridLayout.addWidget(self.pbReset, 4, 3, 1, 1)
        self.pbStop = QtWidgets.QPushButton(self.centralwidget)
        self.pbStop.setEnabled(False)
        self.pbStop.setMaximumSize(QtCore.QSize(16777215, 30))
        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(True)
        font.setUnderline(False)
        font.setWeight(75)
        self.pbStop.setFont(font)
        self.pbStop.setToolTip("")
        self.pbStop.setStyleSheet("background-color: rgb(255, 89, 89)")
        self.pbStop.setObjectName("pbStop")
        self.gridLayout.addWidget(self.pbStop, 3, 3, 1, 1)
        self.pbPause = QtWidgets.QPushButton(self.centralwidget)
        self.pbPause.setEnabled(False)
        self.pbPause.setMaximumSize(QtCore.QSize(16777215, 25))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.pbPause.setFont(font)
        self.pbPause.setStyleSheet("background-color: rgb(252, 233, 79)")
        self.pbPause.setObjectName("pbPause")
        self.gridLayout.addWidget(self.pbPause, 1, 3, 1, 1)
        self.horizontalLayout.addLayout(self.gridLayout)
        self.log = QtWidgets.QTextBrowser(self.centralwidget)
        self.log.setMinimumSize(QtCore.QSize(300, 120))
        self.log.setMaximumSize(QtCore.QSize(300, 160))
        self.log.setObjectName("log")
        self.horizontalLayout.addWidget(self.log)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.image_stack = QtWidgets.QLabel(self.centralwidget)
        self.image_stack.setMinimumSize(QtCore.QSize(200, 200))
        self.image_stack.setText("")
        self.image_stack.setPixmap(QtGui.QPixmap("dslr-camera.svg"))
        self.image_stack.setScaledContents(False)
        self.image_stack.setAlignment(QtCore.Qt.AlignCenter)
        self.image_stack.setObjectName("image_stack")
        self.verticalLayout.addWidget(self.image_stack)
        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line.setLineWidth(2)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setObjectName("line")
        self.verticalLayout.addWidget(self.line)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_3.addWidget(self.label_2)
        self.contrast_slider = QtWidgets.QSlider(self.centralwidget)
        self.contrast_slider.setEnabled(False)
        self.contrast_slider.setMinimumSize(QtCore.QSize(250, 0))
        self.contrast_slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.contrast_slider.setMinimum(1)
        self.contrast_slider.setMaximum(1000)
        self.contrast_slider.setProperty("value", 10)
        self.contrast_slider.setOrientation(QtCore.Qt.Horizontal)
        self.contrast_slider.setObjectName("contrast_slider")
        self.horizontalLayout_3.addWidget(self.contrast_slider)
        self.contrast = QtWidgets.QLabel(self.centralwidget)
        self.contrast.setMinimumSize(QtCore.QSize(21, 0))
        self.contrast.setMaximumSize(QtCore.QSize(16777215, 20))
        self.contrast.setObjectName("contrast")
        self.horizontalLayout_3.addWidget(self.contrast)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_4.addWidget(self.label_3)
        self.brightness_slider = QtWidgets.QSlider(self.centralwidget)
        self.brightness_slider.setEnabled(False)
        self.brightness_slider.setMinimumSize(QtCore.QSize(250, 0))
        self.brightness_slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.brightness_slider.setMinimum(-32000)
        self.brightness_slider.setMaximum(32000)
        self.brightness_slider.setOrientation(QtCore.Qt.Horizontal)
        self.brightness_slider.setObjectName("brightness_slider")
        self.horizontalLayout_4.addWidget(self.brightness_slider)
        self.brightness = QtWidgets.QLabel(self.centralwidget)
        self.brightness.setMinimumSize(QtCore.QSize(43, 0))
        self.brightness.setMaximumSize(QtCore.QSize(16777215, 20))
        self.brightness.setObjectName("brightness")
        self.horizontalLayout_4.addWidget(self.brightness)
        self.verticalLayout_3.addLayout(self.horizontalLayout_4)
        self.line_2 = QtWidgets.QFrame(self.centralwidget)
        self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.verticalLayout_3.addWidget(self.line_2)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label.setObjectName("label")
        self.verticalLayout_3.addWidget(self.label)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_7.setObjectName("label_7")
        self.horizontalLayout_7.addWidget(self.label_7)
        self.R_slider = QtWidgets.QSlider(self.centralwidget)
        self.R_slider.setEnabled(False)
        self.R_slider.setMinimumSize(QtCore.QSize(250, 0))
        self.R_slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.R_slider.setMinimum(1)
        self.R_slider.setMaximum(200)
        self.R_slider.setProperty("value", 100)
        self.R_slider.setSliderPosition(100)
        self.R_slider.setOrientation(QtCore.Qt.Horizontal)
        self.R_slider.setObjectName("R_slider")
        self.horizontalLayout_7.addWidget(self.R_slider)
        self.R_value = QtWidgets.QLabel(self.centralwidget)
        self.R_value.setMinimumSize(QtCore.QSize(30, 0))
        self.R_value.setMaximumSize(QtCore.QSize(16777215, 20))
        self.R_value.setObjectName("R_value")
        self.horizontalLayout_7.addWidget(self.R_value)
        self.verticalLayout_3.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.label_8 = QtWidgets.QLabel(self.centralwidget)
        self.label_8.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_8.setObjectName("label_8")
        self.horizontalLayout_8.addWidget(self.label_8)
        self.G_slider = QtWidgets.QSlider(self.centralwidget)
        self.G_slider.setEnabled(False)
        self.G_slider.setMinimumSize(QtCore.QSize(250, 0))
        self.G_slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.G_slider.setMinimum(1)
        self.G_slider.setMaximum(200)
        self.G_slider.setProperty("value", 100)
        self.G_slider.setOrientation(QtCore.Qt.Horizontal)
        self.G_slider.setObjectName("G_slider")
        self.horizontalLayout_8.addWidget(self.G_slider)
        self.G_value = QtWidgets.QLabel(self.centralwidget)
        self.G_value.setMinimumSize(QtCore.QSize(30, 0))
        self.G_value.setMaximumSize(QtCore.QSize(16777215, 20))
        self.G_value.setObjectName("G_value")
        self.horizontalLayout_8.addWidget(self.G_value)
        self.verticalLayout_3.addLayout(self.horizontalLayout_8)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.label_11 = QtWidgets.QLabel(self.centralwidget)
        self.label_11.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_11.setObjectName("label_11")
        self.horizontalLayout_9.addWidget(self.label_11)
        self.B_slider = QtWidgets.QSlider(self.centralwidget)
        self.B_slider.setEnabled(False)
        self.B_slider.setMinimumSize(QtCore.QSize(250, 0))
        self.B_slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.B_slider.setMinimum(1)
        self.B_slider.setMaximum(200)
        self.B_slider.setProperty("value", 100)
        self.B_slider.setOrientation(QtCore.Qt.Horizontal)
        self.B_slider.setObjectName("B_slider")
        self.horizontalLayout_9.addWidget(self.B_slider)
        self.B_value = QtWidgets.QLabel(self.centralwidget)
        self.B_value.setMinimumSize(QtCore.QSize(30, 0))
        self.B_value.setMaximumSize(QtCore.QSize(16777215, 20))
        self.B_value.setObjectName("B_value")
        self.horizontalLayout_9.addWidget(self.B_value)
        self.verticalLayout_3.addLayout(self.horizontalLayout_9)
        self.line_3 = QtWidgets.QFrame(self.centralwidget)
        self.line_3.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_3.setObjectName("line_3")
        self.verticalLayout_3.addWidget(self.line_3)
        self.label_9 = QtWidgets.QLabel(self.centralwidget)
        self.label_9.setObjectName("label_9")
        self.verticalLayout_3.addWidget(self.label_9)
        self.horizontalLayout_16 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_16.setObjectName("horizontalLayout_16")
        self.label_15 = QtWidgets.QLabel(self.centralwidget)
        self.label_15.setObjectName("label_15")
        self.horizontalLayout_16.addWidget(self.label_15)
        self.horizontalSlider = QtWidgets.QSlider(self.centralwidget)
        self.horizontalSlider.setEnabled(False)
        self.horizontalSlider.setMinimumSize(QtCore.QSize(250, 0))
        self.horizontalSlider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.horizontalSlider.setMaximum(100)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.horizontalLayout_16.addWidget(self.horizontalSlider)
        self.label_17 = QtWidgets.QLabel(self.centralwidget)
        self.label_17.setObjectName("label_17")
        self.horizontalLayout_16.addWidget(self.label_17)
        self.verticalLayout_3.addLayout(self.horizontalLayout_16)
        self.horizontalLayout_17 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_17.setObjectName("horizontalLayout_17")
        self.label_14 = QtWidgets.QLabel(self.centralwidget)
        self.label_14.setObjectName("label_14")
        self.horizontalLayout_17.addWidget(self.label_14)
        self.horizontalSlider_2 = QtWidgets.QSlider(self.centralwidget)
        self.horizontalSlider_2.setMaximum(100)
        self.horizontalSlider_2.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_2.setObjectName("horizontalSlider_2")
        self.horizontalLayout_17.addWidget(self.horizontalSlider_2)
        self.label_18 = QtWidgets.QLabel(self.centralwidget)
        self.label_18.setObjectName("label_18")
        self.horizontalLayout_17.addWidget(self.label_18)
        self.verticalLayout_3.addLayout(self.horizontalLayout_17)
        self.horizontalLayout_18 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_18.setObjectName("horizontalLayout_18")
        self.label_13 = QtWidgets.QLabel(self.centralwidget)
        self.label_13.setObjectName("label_13")
        self.horizontalLayout_18.addWidget(self.label_13)
        self.horizontalSlider_3 = QtWidgets.QSlider(self.centralwidget)
        self.horizontalSlider_3.setMaximum(100)
        self.horizontalSlider_3.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_3.setObjectName("horizontalSlider_3")
        self.horizontalLayout_18.addWidget(self.horizontalSlider_3)
        self.label_19 = QtWidgets.QLabel(self.centralwidget)
        self.label_19.setObjectName("label_19")
        self.horizontalLayout_18.addWidget(self.label_19)
        self.verticalLayout_3.addLayout(self.horizontalLayout_18)
        self.horizontalLayout_15 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_15.setObjectName("horizontalLayout_15")
        self.label_16 = QtWidgets.QLabel(self.centralwidget)
        self.label_16.setObjectName("label_16")
        self.horizontalLayout_15.addWidget(self.label_16)
        self.horizontalSlider_4 = QtWidgets.QSlider(self.centralwidget)
        self.horizontalSlider_4.setMaximum(100)
        self.horizontalSlider_4.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_4.setObjectName("horizontalSlider_4")
        self.horizontalLayout_15.addWidget(self.horizontalSlider_4)
        self.label_20 = QtWidgets.QLabel(self.centralwidget)
        self.label_20.setObjectName("label_20")
        self.horizontalLayout_15.addWidget(self.label_20)
        self.verticalLayout_3.addLayout(self.horizontalLayout_15)
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.label_12 = QtWidgets.QLabel(self.centralwidget)
        self.label_12.setObjectName("label_12")
        self.horizontalLayout_10.addWidget(self.label_12)
        self.horizontalSlider_5 = QtWidgets.QSlider(self.centralwidget)
        self.horizontalSlider_5.setMaximum(100)
        self.horizontalSlider_5.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_5.setObjectName("horizontalSlider_5")
        self.horizontalLayout_10.addWidget(self.horizontalSlider_5)
        self.label_21 = QtWidgets.QLabel(self.centralwidget)
        self.label_21.setObjectName("label_21")
        self.horizontalLayout_10.addWidget(self.label_21)
        self.verticalLayout_3.addLayout(self.horizontalLayout_10)
        self.horizontalLayout_2.addLayout(self.verticalLayout_3)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_5.addWidget(self.label_5)
        self.black_slider = QtWidgets.QSlider(self.centralwidget)
        self.black_slider.setEnabled(False)
        self.black_slider.setMinimumSize(QtCore.QSize(250, 0))
        self.black_slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.black_slider.setMaximum(65535)
        self.black_slider.setOrientation(QtCore.Qt.Horizontal)
        self.black_slider.setObjectName("black_slider")
        self.horizontalLayout_5.addWidget(self.black_slider)
        self.black = QtWidgets.QLabel(self.centralwidget)
        self.black.setMinimumSize(QtCore.QSize(43, 0))
        self.black.setMaximumSize(QtCore.QSize(16777215, 20))
        self.black.setObjectName("black")
        self.horizontalLayout_5.addWidget(self.black)
        self.verticalLayout_2.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_6.addWidget(self.label_6)
        self.white_slider = QtWidgets.QSlider(self.centralwidget)
        self.white_slider.setEnabled(False)
        self.white_slider.setMinimumSize(QtCore.QSize(250, 0))
        self.white_slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.white_slider.setMaximum(65535)
        self.white_slider.setSliderPosition(65535)
        self.white_slider.setOrientation(QtCore.Qt.Horizontal)
        self.white_slider.setObjectName("white_slider")
        self.horizontalLayout_6.addWidget(self.white_slider)
        self.white = QtWidgets.QLabel(self.centralwidget)
        self.white.setMinimumSize(QtCore.QSize(43, 0))
        self.white.setMaximumSize(QtCore.QSize(16777215, 20))
        self.white.setObjectName("white")
        self.horizontalLayout_6.addWidget(self.white)
        self.verticalLayout_2.addLayout(self.horizontalLayout_6)
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.cbSCNR = QtWidgets.QCheckBox(self.centralwidget)
        self.cbSCNR.setMaximumSize(QtCore.QSize(16777215, 30))
        self.cbSCNR.setObjectName("cbSCNR")
        self.horizontalLayout_13.addWidget(self.cbSCNR)
        self.cmSCNR = QtWidgets.QComboBox(self.centralwidget)
        self.cmSCNR.setEnabled(False)
        self.cmSCNR.setMaximumSize(QtCore.QSize(16777215, 30))
        self.cmSCNR.setObjectName("cmSCNR")
        self.cmSCNR.addItem("")
        self.cmSCNR.addItem("")
        self.cmSCNR.addItem("")
        self.cmSCNR.addItem("")
        self.horizontalLayout_13.addWidget(self.cmSCNR)
        self.SCNR_Slider = QtWidgets.QSlider(self.centralwidget)
        self.SCNR_Slider.setEnabled(False)
        self.SCNR_Slider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.SCNR_Slider.setMaximum(100)
        self.SCNR_Slider.setProperty("value", 50)
        self.SCNR_Slider.setOrientation(QtCore.Qt.Horizontal)
        self.SCNR_Slider.setObjectName("SCNR_Slider")
        self.horizontalLayout_13.addWidget(self.SCNR_Slider)
        self.SCNR_value = QtWidgets.QLabel(self.centralwidget)
        self.SCNR_value.setMinimumSize(QtCore.QSize(30, 0))
        self.SCNR_value.setMaximumSize(QtCore.QSize(16777215, 20))
        self.SCNR_value.setObjectName("SCNR_value")
        self.horizontalLayout_13.addWidget(self.SCNR_value)
        self.horizontalLayout_12.addLayout(self.horizontalLayout_13)
        self.verticalLayout_2.addLayout(self.horizontalLayout_12)
        self.horizontalLayout_2.addLayout(self.verticalLayout_2)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.pb_apply_value = QtWidgets.QPushButton(self.centralwidget)
        self.pb_apply_value.setEnabled(False)
        self.pb_apply_value.setMaximumSize(QtCore.QSize(16777215, 30))
        self.pb_apply_value.setObjectName("pb_apply_value")
        self.verticalLayout.addWidget(self.pb_apply_value)
        stack_window.setCentralWidget(self.centralwidget)
        self.actionQuit = QtWidgets.QAction(stack_window)
        self.actionQuit.setObjectName("actionQuit")

        self.retranslateUi(stack_window)
        self.cbSCNR.clicked['bool'].connect(self.SCNR_Slider.setEnabled)
        self.cbAlign.clicked['bool'].connect(self.cmMode.setEnabled)
        self.cbSCNR.clicked['bool'].connect(self.cmSCNR.setEnabled)
        self.actionQuit.triggered.connect(stack_window.close)
        self.cbDark.clicked['bool'].connect(self.tDark.setEnabled)
        self.cbDark.clicked['bool'].connect(self.bBrowseDark.setEnabled)
        self.horizontalSlider.valueChanged['int'].connect(self.label_17.setNum)
        self.horizontalSlider_2.valueChanged['int'].connect(self.label_18.setNum)
        self.horizontalSlider_3.valueChanged['int'].connect(self.label_19.setNum)
        self.horizontalSlider_4.valueChanged['int'].connect(self.label_20.setNum)
        self.horizontalSlider_5.valueChanged['int'].connect(self.label_21.setNum)
        QtCore.QMetaObject.connectSlotsByName(stack_window)

    def retranslateUi(self, stack_window):
        _translate = QtCore.QCoreApplication.translate
        stack_window.setWindowTitle(_translate("stack_window", "Astro Live Stacker"))
        self.cbKeep.setText(_translate("stack_window", "Conserver les images"))
        self.bBrowseWork.setText(_translate("stack_window", "Rep. wrk"))
        self.cbAlign.setText(_translate("stack_window", "Aligner"))
        self.cmMode.setItemText(0, _translate("stack_window", "Sum"))
        self.cmMode.setItemText(1, _translate("stack_window", "Mean"))
        self.bBrowseDark.setText(_translate("stack_window", "Fic. dark"))
        self.label_10.setText(_translate("stack_window", "Tempo"))
        self.label_4.setText(_translate("stack_window", "ms"))
        self.tScan.setText(_translate("stack_window", "~/als/scan"))
        self.tDark.setText(_translate("stack_window", "~/als/dark.fits"))
        self.cnt.setText(_translate("stack_window", "0"))
        self.bBrowseFolder.setText(_translate("stack_window", "Rep. scan"))
        self.cbWww.setText(_translate("stack_window", "www"))
        self.tWork.setText(_translate("stack_window", "~/als/wrk"))
        self.cbDark.setText(_translate("stack_window", "Utiliser un dark"))
        self.pbPlay.setText(_translate("stack_window", "Play"))
        self.pbSave.setText(_translate("stack_window", "Save"))
        self.pbReset.setText(_translate("stack_window", "Reset"))
        self.pbStop.setText(_translate("stack_window", "Stop"))
        self.pbPause.setText(_translate("stack_window", "Pause"))
        self.label_2.setText(_translate("stack_window", "Contrast :"))
        self.contrast.setText(_translate("stack_window", "1"))
        self.label_3.setText(_translate("stack_window", "Brightness :"))
        self.brightness.setText(_translate("stack_window", "0"))
        self.label.setText(_translate("stack_window", "RGB :"))
        self.label_7.setText(_translate("stack_window", "R :"))
        self.R_value.setText(_translate("stack_window", "1"))
        self.label_8.setText(_translate("stack_window", "G :"))
        self.G_value.setText(_translate("stack_window", "1"))
        self.label_11.setText(_translate("stack_window", "B :"))
        self.B_value.setText(_translate("stack_window", "1"))
        self.label_9.setText(_translate("stack_window", "Wavelets"))
        self.label_15.setText(_translate("stack_window", "Level 1:"))
        self.label_17.setText(_translate("stack_window", "TextLabel"))
        self.label_14.setText(_translate("stack_window", "Level 2:"))
        self.label_18.setText(_translate("stack_window", "TextLabel"))
        self.label_13.setText(_translate("stack_window", "Level 3:"))
        self.label_19.setText(_translate("stack_window", "TextLabel"))
        self.label_16.setText(_translate("stack_window", "Level 4:"))
        self.label_20.setText(_translate("stack_window", "TextLabel"))
        self.label_12.setText(_translate("stack_window", "Level 5:"))
        self.label_21.setText(_translate("stack_window", "TextLabel"))
        self.label_5.setText(_translate("stack_window", "Black/Min :"))
        self.black.setText(_translate("stack_window", "0"))
        self.label_6.setText(_translate("stack_window", "White/Max :"))
        self.white.setText(_translate("stack_window", "65535"))
        self.cbSCNR.setText(_translate("stack_window", "SCNR"))
        self.cmSCNR.setItemText(0, _translate("stack_window", "Av Neutral"))
        self.cmSCNR.setItemText(1, _translate("stack_window", "Max Neutral"))
        self.cmSCNR.setItemText(2, _translate("stack_window", "Add Mask"))
        self.cmSCNR.setItemText(3, _translate("stack_window", "Max Mask"))
        self.SCNR_value.setText(_translate("stack_window", "0.50"))
        self.pb_apply_value.setText(_translate("stack_window", "Apply"))
        self.actionQuit.setText(_translate("stack_window", "&Quit"))




if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    stack_window = QtWidgets.QMainWindow()
    ui = Ui_stack_window()
    ui.setupUi(stack_window)
    stack_window.show()
    sys.exit(app.exec_())
