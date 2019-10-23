"""
Our custom widgets
"""
import math
import typing

import numpy as np

from PyQt5 import QtGui
from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QSlider, QGraphicsView, QWidget

from als.code_utilities import log
from als.model.data import DYNAMIC_DATA

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


class ImageView(QGraphicsView):
    """
    The main image view.

    Subclasses QGraphicsView to add mousewheel zoom features
    """

    _ZOOM_SCALE_RATIO = 1.1

    @log
    def __init__(self, parent: typing.Optional[QWidget] = ...):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    # pylint: disable=C0103
    @log
    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """
        Performs zoom in & out according to mousewheel moves

        :param event: The Qt wheel event
        :type event: QtGui.QWheelEvent
        """
        if event.angleDelta().y() > 0:
            self.scale(self._ZOOM_SCALE_RATIO, self._ZOOM_SCALE_RATIO)
        elif event.angleDelta().y() < 0:
            self.scale(1 / self._ZOOM_SCALE_RATIO, 1 / self._ZOOM_SCALE_RATIO)


class HistogramView(QWidget):

    _BIN_COUNT = 512

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._image = None
        self._histogram = None
        self._painter = QPainter()
        DYNAMIC_DATA.add_observer(self)

    @log
    def update_display(self, image_only: bool = False):

        if image_only:

            image = DYNAMIC_DATA.process_result

            if image is not None:
                self._image = image
                self._histogram = self._compute_histogram()
                self.update()

    def paintEvent(self, event):

        if self.isVisible() and self._histogram is not None:

            self._painter.begin(self)
            self._painter.setRenderHint(QPainter.Antialiasing, True)
            self._painter.translate(QPoint(0, 0))

            # remove first and last items of the histogram
            # so we don't end up with a vertically squashed display
            # when histogram is clipping on black or white
            tweaked_histogram = np.delete(self._histogram, [0, self._BIN_COUNT - 1])

            max_value = tweaked_histogram.max()

            for i, value in enumerate(tweaked_histogram):

                x = round(i / self._BIN_COUNT * self.width())
                bar_height = round(value / max_value * self.height())

                self._painter.save()
                self._painter.setPen(QPen(Qt.white))
                self._painter.drawLine(x,
                                       self.height(),
                                       x,
                                       self.height() - bar_height)
                self._painter.restore()

            self._painter.end()

    def _compute_histogram(self):

        return np.histogram(self._image.data, self._BIN_COUNT)[0]
