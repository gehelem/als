"""
Provide factories for GUI items
"""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSlider, QLabel, QHBoxLayout, QWidget

from als.code_utilities import log, AlsException
from als.model.params import ProcessingParameter, RangeParameter

_LOGGER = logging.getLogger(__name__)


class UnsupportedParameter(AlsException):
    """Raised when trying to create widget for an unknown parameter type"""


class ProcessingControlFactory:

    @staticmethod
    @log
    def create_widget(param: ProcessingParameter) -> QWidget:

        if isinstance(param, RangeParameter):

            slider = QSlider()
            slider.setToolTip(param.description)
            slider.setMinimum(0)
            slider.setMaximum(255)
            slider.setSingleStep(255 / param.steps)
            slider.setPageStep(slider.singleStep() * 10)
            slider.setOrientation(Qt.Horizontal)

            return slider

        raise UnsupportedParameter("Unhandled param type", f"{type(param)} is unknown")
