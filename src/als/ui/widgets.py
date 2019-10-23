"""
Our custom widgets
"""
from PyQt5.QtWidgets import QSlider


DEFAULT_SLIDER_MAX = 255


class Slider(QSlider):
    """
    A slider that has a default value and resets to it when double-clicked
    """

    def __init__(self, parent=None):

        super().__init__(parent)
        self._default_value = 0

    def set_default_value(self, default_value):
        """
        Sets the slider default value

        :param default_value: the default value
        :type default_value: int
        """

        self._default_value = default_value

    # pylint: disable=C0103
    def mouseDoubleClickEvent(self, _):
        """
        User double-clicked the slider

        :param _: ignored Qt event
        """

        self.setValue(self._default_value)
