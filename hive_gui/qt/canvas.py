from QT.QtGui import *


class NodeCanvas(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.setWindowTitle("Hive Canvas")

        self._main_layout = QVBoxLayout(self)
        self.setLayout(self._main_layout)
        self.setContentsMargins(5, 5, 5, 5)

        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(5)

        self._node_view = None

    def set_node_view(self, nodeView):
        assert self._node_view is None
        self._node_view = nodeView
        self._main_layout.addWidget(self._node_view)
