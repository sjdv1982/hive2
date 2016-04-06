from PyQt5.QtCore import QEvent, pyqtSignal, QPoint
from PyQt5.QtWebKitWidgets import QWebView


class QEditorWebView(QWebView):
    on_drag_move = pyqtSignal(QEvent)
    on_dropped = pyqtSignal(QEvent, QPoint)

    def __init__(self, parent=None):
        QWebView.__init__(self, parent)

        self.setAcceptDrops(True)

    def dragMoveEvent(self, event):
        self.on_drag_move.emit(event)

    def dropEvent(self, event):
        global_pos = self.mapToGlobal(event.pos())
        self.on_dropped.emit(event, global_pos)
