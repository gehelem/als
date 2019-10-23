"""
Our custom widgets
"""
import logging
import typing

import numpy as np
from PyQt5 import QtGui
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QSlider, QGraphicsView, QWidget

from als.code_utilities import log
from als.model.data import DYNAMIC_DATA

_LOGGER = logging.getLogger(__name__)

DEFAULT_SLIDER_MAX = 255


class Slider(QSlider):
    """
    A slider that has a default value and resets to it when double-clicked
    """

    @log
    def __init__(self, parent=None):

        super().__init__(parent)
        self._default_value = 0

    @log
    def set_default_value(self, default_value):
        """
        Sets the slider default value

        :param default_value: the default value
        :type default_value: int
        """

        self._default_value = default_value

    # pylint: disable=C0103
    @log
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

    # pylint: disable=C0103
    def mouseDoubleClickEvent(self, _):
        """
        Reacts to a double-click in image view : Fit image in view

        :param _: ignored Qt event
        """

        self.fitInView(self.scene().items()[0], Qt.KeepAspectRatio)


class HistogramView(QWidget):
    """
    Our main histogram display
    """

    _BIN_COUNT = 512

    @log
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._image = None
        self._histogram = None
        self._painter = QPainter()
        DYNAMIC_DATA.add_observer(self)

    @log
    def update_display(self, image_only: bool = False):
        """
        Update display, duh !

        :param image_only: are we receiving a notification that a new processing result is ready ?
        :type image_only: bool
        """

        if image_only:

            image = DYNAMIC_DATA.process_result

            if image is not None:
                self._image = image
                self._histogram = self._compute_histogram()
                self.update()

    # pylint: disable=C0103
    @log
    def paintEvent(self, _):
        """
        Do the painting, Leonardo !

        :param _: ignored Qt event
        """

        if self.isVisible():

            self._painter.begin(self)
            self._painter.setRenderHint(QPainter.Antialiasing, True)
            self._painter.translate(QPoint(0, 0))

            if self._histogram is not None:
                # remove first and last items of a copy of the histogram before getting max value
                # so we don't end up with a vertically squashed display
                # when histogram is clipping on black or white
                tweaked_histogram = np.delete(self._histogram, [0, self._BIN_COUNT - 1])
                max_value = tweaked_histogram.max()

                # in some very rare cases (like playing with an image of pure single primary color)
                # max_value will be 0 after removing the 2 extreme bins of the original histogram
                #
                # in that case, we replace this 0 with the original histogram's max value
                if max_value == 0:
                    max_value = self._histogram.max()

                for i, value in enumerate(self._histogram):

                    x = round(i / self._BIN_COUNT * self.width())
                    bar_height = round(value / max_value * self.height())

                    self._painter.save()
                    pen = QPen(Qt.white)
                    pen.setWidth(2)
                    self._painter.setPen(pen)
                    self._painter.drawLine(x,
                                           self.height(),
                                           x,
                                           self.height() - bar_height)
                    self._painter.restore()

            else:
                font_inspector = self._painter.fontMetrics()
                message = "No data"
                message_height = font_inspector.height()
                message_width = font_inspector.width(message)

                self._painter.drawText(
                    (self.width() - message_width) / 2,
                    ((self.height() - message_height) / 2) + message_height,
                    "No data")

            self._painter.end()

    @log
    def _compute_histogram(self):
        """
        Compute histogram
        """

        return np.histogram(self._image.data, self._BIN_COUNT)[0]
