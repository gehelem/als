"""
Provide factories for GUI items
"""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSlider, QLabel, QHBoxLayout

from als.code_utilities import log, AlsException
from als.model.params import ProcessingParameter, RangeParameter

_LOGGER = logging.getLogger(__name__)


class UnsupportedParameter(AlsException):
    """Raised when trying to create widget for an unknown parameter type"""


class ProcessingControlFactory:

    @staticmethod
    @log
    def create_widget(param: ProcessingParameter):

        if isinstance(param, RangeParameter):

            slider = QSlider()
            slider.setToolTip(param.description)
            slider.setMinimum(0)
            slider.setMask(255)
            slider.setSingleStep(255 / param.steps)
            slider.setPageStep(slider.singleStep() * 10)
            slider.setOrientation(Qt.Horizontal)

            label = QLabel()
            label.setText(param.name)

            box = QHBoxLayout()
            box.addItem(label)
            box.addItem(slider)

            return box

        raise UnsupportedParameter("Unhandled param type", f"{type(param)} is unknown")
