from PyQt5.QtCore import QEvent, pyqtSignal, QPoint
from PyQt5.QtWebEngineWidgets import QWebEngineView


class QEditorWebView(QWebEngineView):
    onDragMove = pyqtSignal(QEvent)
    onDropped = pyqtSignal(QEvent, QPoint)

    def __init__(self, parent=None):
        super(QEditorWebView, self).__init__(parent)

        self.setAcceptDrops(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        self.onDragMove.emit(event)

    def dropEvent(self, event):
        global_pos = self.mapToGlobal(event.pos())
        self.onDropped.emit(event, global_pos)
