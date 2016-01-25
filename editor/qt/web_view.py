from .qt_webkit import QWebView


class QEditorWebView(QWebView):

    def __init__(self, parent=None):
        QWebView.__init__(self, parent)

        self.on_drag_enter = None

    def dragEnterEvent(self, event):
        if callable(self.on_drag_enter):
            pos = event.pos()
            position = pos.x(), pos.y()
            self.on_drag_enter(position)
