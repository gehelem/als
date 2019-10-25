"""
Our custom widgets
"""
import logging
import typing

from PyQt5 import QtGui
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QSlider, QGraphicsView, QWidget

from als.code_utilities import log
from als.model.data import DYNAMIC_DATA

_LOGGER = logging.getLogger(__name__)


class Slider(QSlider):
    """
    A slider that has a default value and resets to it when double-clicked
    """

    MAX_VALUE = 255

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

    _ZOOM_FACTOR = 1.1

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
            self.scale(ImageView._ZOOM_FACTOR, ImageView._ZOOM_FACTOR)
        elif event.angleDelta().y() < 0:
            self.scale(1 / ImageView._ZOOM_FACTOR, 1 / ImageView._ZOOM_FACTOR)

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

    _TOP_MARGIN_IN_PX = 5

    @log
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._painter = QPainter()

        self._color_pens = [QPen(Qt.red), QPen(Qt.green), QPen(Qt.blue)]
        for pen in self._color_pens:
            pen.setWidth(2)

        self._white_pen = QPen(Qt.white)
        self._white_pen.setWidth(2)

    # pylint: disable=C0103
    @log
    def paintEvent(self, _):
        """
        Do the painting, Leonardo !

        :param _: ignored Qt event
        """

        if self.isVisible():

            self._painter.begin(self)
            self._painter.translate(QPoint(0, 0))

            if DYNAMIC_DATA.histogram_container is not None:

                histograms = DYNAMIC_DATA.histogram_container.get_histograms()
                bin_count = DYNAMIC_DATA.histogram_container.bin_count
                global_maximum = DYNAMIC_DATA.histogram_container.global_maximum

                if len(histograms) > 1:
                    pens = self._color_pens
                    self._painter.setCompositionMode(QPainter.CompositionMode_Plus)
                else:
                    pens = [self._white_pen]
                    histograms = [histograms[0]]
                    self._painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                for pen, histogram in zip(pens, histograms):

                    self._painter.save()
                    self._painter.setPen(pen)

                    for i, value in enumerate(histogram):

                        x = round(i / bin_count * self.width())
                        bar_height = round(value / global_maximum * self.height())

                        self._painter.drawLine(
                            x,
                            self.height(),
                            x,
                            self.height() - (bar_height - HistogramView._TOP_MARGIN_IN_PX))

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
