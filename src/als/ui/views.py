"""
Provide various views used in the GUI
"""
import logging
import typing

from PyQt5 import QtGui
from PyQt5.QtWidgets import QGraphicsView, QWidget
from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)


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
