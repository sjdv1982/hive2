from PySide.QtCore import *
from PySide.QtGui import *

area_classes = {
    "left": Qt.LeftDockWidgetArea,
    "right": Qt.RightDockWidgetArea,
    "top": Qt.TopDockWidgetArea,
    "bottom": Qt.BottomDockWidgetArea,
}


class MainWindow(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

    def create_subwindow(self, title, position):
        area = area_classes[position]
        window = QDockWidget(title, self)
        child = QWidget()
        window.setWidget(child)
        self.addDockWidget(area, window)
        return window