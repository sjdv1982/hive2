from .qt_webkit import QWebView


class QEditorWebView(QWebView):

    def __init__(self, parent=None):
        QWebView.__init__(self, parent)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        event.ignore()
