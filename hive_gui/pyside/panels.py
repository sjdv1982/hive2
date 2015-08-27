from PySide.QtGui import *
from functools import partial


from .utils import create_widget


class ConfigurationPanel(QWidget):

    def __init__(self, node_manager):
        QWidget.__init__(self)

        self._node = None
        self._node_manager = node_manager

        self._layout = QFormLayout()
        self.setLayout(self._layout)

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, node):
        self._node = node

        self.on_node_updated(node)

    def _rename_node(self, node, name):
        self._node_manager.set_node_name(node, name)

    def on_node_updated(self, node):
        layout = self._layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

        widget = QLabel(node.hive_path)
        widget.setStyleSheet("QLabel {text-decoration: underline; color:#858585; }")
        layout.addRow(self.tr("Import path"), widget)

        widget = QLineEdit()
        widget.setPlaceholderText(node.name)
        widget.textChanged.connect(partial(self._rename_node, node))
        layout.addRow(self.tr("&Name"), widget)


class FoldingPanel(QWidget):

    def __init__(self, fold_node_path, node_manager):
        QWidget.__init__(self)

        self._node = None
        self._fold_node_path = fold_node_path
        self._node_manager = node_manager

        self._folding_layout = QFormLayout()
        self.setLayout(self._folding_layout)

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, node):
        self._node = node

        self.on_node_updated(node)

    def _fold_antenna(self, pin):
        self._node_manager.fold_pin(pin)
        self.on_node_updated(pin.node)

    def _unfold_antenna(self, pin):
        self._node_manager.unfold_pin(pin)
        self.on_node_updated(pin.node)

    def on_node_updated(self, node):
        layout = self._folding_layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

        for name, pin in node.inputs.items():
            if pin.mode != "pull":
                continue

            if self._node_manager.can_fold_pin(pin):
                button = QPushButton("&Fold")
                on_clicked = partial(self._fold_antenna, pin)

                layout.addRow(self.tr(name), button)
                button.clicked.connect(on_clicked)

            elif pin.is_folded:
                button = QPushButton("&Unfold")
                on_clicked = partial(self._unfold_antenna, pin)

                layout.addRow(self.tr(name), button)
                button.clicked.connect(on_clicked)

                value = create_widget(pin.data_type)
                layout.addWidget(value)

            else:
                continue