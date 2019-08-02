"""
provides ways to show messages to app user
"""
from PyQt5.QtWidgets import QMessageBox


def warning_box(title, message):
    message_box('Warning : ' + title, message, QMessageBox.Warning)


def error_box(title, message):
    message_box('Error : ' + title, message, QMessageBox.Critical)


def message_box(title, message, icon=QMessageBox.Information):
    box = QMessageBox()
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(message)
    box.exec()
