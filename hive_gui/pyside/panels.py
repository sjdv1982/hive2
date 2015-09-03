from PySide.QtGui import *
from functools import partial


from .utils import create_widget
from ..utils import infer_type
from ..node import NodeTypes


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

        if node is None:
            return

        widget = QLabel(node.import_path)
        widget.setStyleSheet("QLabel {text-decoration: underline; color:#858585; }")
        layout.addRow(self.tr("Import path"), widget)

        widget = QLineEdit()
        widget.setPlaceholderText(node.name)
        widget.textChanged.connect(partial(self._rename_node, node))
        layout.addRow(self.tr("&Name"), widget)


class ArgsPanel(QWidget):

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

    def on_node_updated(self, node):
        layout = self._layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

        if node is None:
            return

        # Meta Args
        meta_args = node.params.get('meta_args')
        if meta_args:
            for name, value in meta_args.items():
                data_type = infer_type(value, allow_object=True)
                widget, controller = create_widget(data_type)
                widget.setEnabled(False)
                controller.value = repr(value)

                layout.addRow(self.tr(name), widget)

        # Args
        args = node.params.get('args')
        if args:
            # Divider if required
            if meta_args:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                layout.addRow(line)

            for name, value in args.items():
                data_type = infer_type(value, allow_object=True)

                # HACKY XXX
                is_code_field = name == "code"

                widget, controller = create_widget(data_type, use_text_area=is_code_field)
                widget.controller = controller

                # HACKY XXX
                if is_code_field:
                    widget.setCurrentFont(QFont("Consolas"))

                def on_changed(value, name=name, args=args):
                    args[name] = value

                controller.on_changed = on_changed
                controller.value = value

                layout.addRow(self.tr(name), widget)

        # Class Args
        cls_args = node.params.get('cls_args')
        if cls_args:
            # Divider if required
            if cls_args or meta_args:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                layout.addRow(line)

            for name, value in cls_args.items():
                data_type = infer_type(value, allow_object=True)

                widget, controller = create_widget(data_type)
                widget.controller = controller

                def on_changed(value, name=name, cls_args=cls_args):
                    cls_args[name] = value

                controller.on_changed = on_changed
                controller.value = value

                layout.addRow(self.tr(name), widget)


class FoldingPanel(QWidget):

    def __init__(self, node_manager):
        QWidget.__init__(self)

        self._node = None
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

        if node is None:
            return

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

                widget = ArgsPanel(node_manager=None)

                target_connection = next(iter(pin.connections))
                target_pin = target_connection.output_pin
                widget.node = target_pin.node

                layout.addWidget(widget)

            else:
                continue