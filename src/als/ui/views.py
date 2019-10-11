import typing

from PyQt5 import QtGui
from PyQt5.QtWidgets import QGraphicsView, QWidget


class ImageView(QGraphicsView):
    def __init__(self, parent: typing.Optional[QWidget] = ...) -> None:
        super().__init__(parent)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        scale_ratio = 1.1

        if event.angleDelta().y() > 0:
            self.scale(scale_ratio, scale_ratio)
        elif event.angleDelta().y() < 0:
            self.scale(1/scale_ratio, 1/scale_ratio)



