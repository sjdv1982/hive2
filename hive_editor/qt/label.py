from .qt_core import *
from .qt_gui import *


class QClickableLabel(QLabel):

    clicked = Signal()

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))

    def enterEvent(self, event):
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
