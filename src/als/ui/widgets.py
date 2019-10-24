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
    _DISPLAY_TOP_MARGIN_IN_PX = 5

    @log
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._histograms = None
        self._painter = QPainter()

        self._color_pens = [QPen(Qt.red), QPen(Qt.green), QPen(Qt.blue)]
        for pen in self._color_pens:
            pen.setWidth(2)

        self._white_pen = QPen(Qt.white)
        self._white_pen.setWidth(2)

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
                self._compute_histograms(image)
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
            self._painter.translate(QPoint(0, 0))

            if self._histograms is not None:

                # We first need to find the global maximum among our histograms
                #
                # We remove first and last item of a copy of each histogram before getting its max value
                # so we don't end up with a vertically squashed display if histogram is clipping on black or white
                global_maximum = max([tweaked_histogram.max() for tweaked_histogram in [
                    np.delete(histogram, [0, self._BIN_COUNT - 1]) for histogram in self._histograms
                ]])

                if global_maximum == 0:
                    # In some very rare cases, i.e. playing with images of pure single primary colors,
                    # the global maximum will be 0 after removing the 2 extreme bins of the original histograms
                    #
                    # As only Chuck Norris can divide by zero, we replace this 0 with the global maximum
                    # among our *original* histograms
                    global_maximum = max([original_histo.max() for original_histo in self._histograms])

                if len(self._histograms) > 1:
                    pens = self._color_pens
                    histograms = self._histograms
                    self._painter.setCompositionMode(QPainter.CompositionMode_Plus)
                else:
                    pens = [self._white_pen]
                    histograms = [self._histograms[0]]
                    self._painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                for pen, histogram in zip(pens, histograms):

                    self._painter.save()
                    self._painter.setPen(pen)

                    for i, value in enumerate(histogram):

                        x = round(i / self._BIN_COUNT * self.width())
                        bar_height = round(value / global_maximum * self.height())

                        self._painter.drawLine(
                            x,
                            self.height(),
                            x,
                            self.height() - (bar_height - self._DISPLAY_TOP_MARGIN_IN_PX))

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
    def _compute_histograms(self, image):
        """
        Compute histograms
        """
        if image.is_color():

            histograms = list()
            for channel in range(3):
                histograms.append(np.histogram(image.data[:, :, channel], self._BIN_COUNT)[0])
                self._histograms = histograms
        else:
            self._histograms = [np.histogram(image.data, self._BIN_COUNT)[0]]
