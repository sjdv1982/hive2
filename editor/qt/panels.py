from functools import partial
from webbrowser import open as open_url

from .label import QClickableLabel
from .qt_gui import *
from .utils import create_widget
from ..utils import import_module_from_path


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
        self._node_manager.rename_node(node, name)

    def _import_path_clicked(self, import_path):
        module, class_name = import_module_from_path(import_path)
        open_url(module.__file__)

    def on_node_updated(self, node):
        layout = self._layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

        if node is None:
            return

        widget = QClickableLabel(node.import_path)
        widget.clicked.connect(partial(self._import_path_clicked, node.import_path))

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
            meta_arg_data = node.params_info["meta_args"]

            layout.addRow(QLabel("Meta Args:"))

            for name, value in meta_args.items():
                try:
                    inspector_option = meta_arg_data[name]

                # This happens with hidden args passed to factory (currently only exists for meta args [hive.pull/push in/out])
                except KeyError:
                    continue

                # Get data type
                data_type = inspector_option.data_type

                widget, controller = create_widget(data_type)
                widget.setEnabled(False)
                controller.value = value

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

            arg_data = node.params_info["args"]

            layout.addRow(QLabel("Args:"))

            for name, value in args.items():
                # Get data type
                inspector_option = arg_data[name]
                data_type = inspector_option.data_type

                widget, controller = create_widget(data_type)
                widget.controller = controller

                def on_changed(value, name=name, args=args):
                    args[name] = value

                controller.on_changed = on_changed
                controller.value = value

                layout.addRow(self.tr(name), widget)

        # Class Args
        cls_args = node.params.get('cls_args')
        if cls_args:
            # Divider if required
            if meta_args or args:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                layout.addRow(line)

            cls_arg_data = node.params_info["cls_args"]

            layout.addRow(QLabel("Cls Args:"))

            for name, value in cls_args.items():
                # Get data type
                inspector_option = cls_arg_data[name]
                data_type = inspector_option.data_type

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

            if pin.is_foldable:
                button = QPushButton("Fol&d")
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