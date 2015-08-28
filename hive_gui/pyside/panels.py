from PySide.QtGui import *
from functools import partial


from .utils import create_widget
from ..utils import infer_type


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


class ArgsPanel(QWidget):

    def __init__(self):
        QWidget.__init__(self)

        self._node = None

        self._layout = QFormLayout()
        self.setLayout(self._layout)

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, node):
        self._node = node

        self.on_node_updated(node)

    def on_node_updated(self, node):
        layout = self._layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

        # Args
        has_args = 'args' in node.params
        if has_args:
            args = node.params['args']
            for name, value in args.items():
                data_type = infer_type(value)

                widget, controller = create_widget(data_type)
                widget.controller = controller

                def on_changed(value, args=args):
                    args[name] = value

                controller.on_changed = on_changed
                controller.value = value

                layout.addRow(self.tr(name), widget)

        # Class Args
        if 'cls_args' in node.params:
            # Divider if required
            if has_args:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                layout.addRow(line)

            cls_args = node.params['cls_args']
            for name, value in cls_args.items():
                data_type = infer_type(value)

                widget, controller = create_widget(data_type)
                widget.controller = controller

                def on_changed(value, cls_args=cls_args):
                    cls_args[name] = value

                controller.on_changed = on_changed
                controller.value = value

                layout.addRow(self.tr(name), widget)


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

                # TODO check if we should just naively use x.data_type[0]
                widget, controller = create_widget(pin.data_type[0])
                layout.addWidget(widget)

                controller.on_changed = partial(self._node_manager.set_folded_value, pin)
                controller.value = self._node_manager.get_folded_value(pin)

                widget.controller = controller

            else:
                continue