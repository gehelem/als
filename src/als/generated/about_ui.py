# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/als/about_ui.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        AboutDialog.setObjectName("AboutDialog")
        AboutDialog.setWindowModality(QtCore.Qt.WindowModal)
        AboutDialog.resize(294, 211)
        AboutDialog.setModal(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(AboutDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lblTitle = QtWidgets.QLabel(AboutDialog)
        self.lblTitle.setObjectName("lblTitle")
        self.verticalLayout.addWidget(self.lblTitle)
        self.lblName = QtWidgets.QLabel(AboutDialog)
        self.lblName.setObjectName("lblName")
        self.verticalLayout.addWidget(self.lblName)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lblVersionTitle = QtWidgets.QLabel(AboutDialog)
        self.lblVersionTitle.setObjectName("lblVersionTitle")
        self.horizontalLayout.addWidget(self.lblVersionTitle)
        self.lblVersionValue = QtWidgets.QLabel(AboutDialog)
        self.lblVersionValue.setObjectName("lblVersionValue")
        self.horizontalLayout.addWidget(self.lblVersionValue)
        self.horizontalLayout_2.addLayout(self.horizontalLayout)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem2)
        self.lblLicense = QtWidgets.QLabel(AboutDialog)
        self.lblLicense.setOpenExternalLinks(True)
        self.lblLicense.setObjectName("lblLicense")
        self.horizontalLayout_4.addWidget(self.lblLicense)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem3)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        spacerItem4 = QtWidgets.QSpacerItem(20, 24, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem4)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem5 = QtWidgets.QSpacerItem(118, 17, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem5)
        self.btnOK = QtWidgets.QPushButton(AboutDialog)
        self.btnOK.setObjectName("btnOK")
        self.horizontalLayout_3.addWidget(self.btnOK)
        spacerItem6 = QtWidgets.QSpacerItem(118, 17, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem6)
        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.retranslateUi(AboutDialog)
        self.btnOK.clicked.connect(AboutDialog.accept)
        QtCore.QMetaObject.connectSlotsByName(AboutDialog)

    def retranslateUi(self, AboutDialog):
        _translate = QtCore.QCoreApplication.translate
        AboutDialog.setWindowTitle(_translate("AboutDialog", "About ALS"))
        self.lblTitle.setText(_translate("AboutDialog", "<html><head/><body><p align=\"center\"><span style=\" font-size:22pt;\">ALS</span></p></body></html>"))
        self.lblName.setText(_translate("AboutDialog", "<html><head/><body><p align=\"center\"><span style=\" font-size:16pt;\">Astro Live Stacker</span></p></body></html>"))
        self.lblVersionTitle.setText(_translate("AboutDialog", "Version :"))
        self.lblVersionValue.setText(_translate("AboutDialog", "DUMMY"))
        self.lblLicense.setText(_translate("AboutDialog", "<html><head/><body><p>License : <a href=\"http://www.gnu.org/licenses/gpl-3.0.txt\"><span style=\" text-decoration: underline; color:#2967ca;\">GPLv3</span></a></p></body></html>"))
        self.btnOK.setText(_translate("AboutDialog", "OK"))
