from functools import partial

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QFormLayout, QFrame, QLineEdit, QPushButton

from .label import QClickableLabel
from .utils import create_widget


class NodeContextPanelBase(QWidget):
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

    def _clear_layout(self):
        layout = self._layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def _update_layout(self, node):
        raise NotImplementedError

    def on_node_updated(self, node):
        self._clear_layout()

        if node is None:
            return

        self._update_layout(node)


class ArgumentsPanel(NodeContextPanelBase):
    do_morph_node = pyqtSignal(object)
    set_param_value = pyqtSignal(object, str, str, object)

    def _update_layout(self, node):
        layout = self._layout

        # Meta Args
        meta_args = node.params.get('meta_args')
        if meta_args:
            meta_arg_data = node.params_info["meta_args"]

            # Create container
            box = QFrame()
            layout.addRow(self.tr("Meta Args"), box)

            box.setFrameShape(QFrame.StyledPanel)
            box_layout = QFormLayout()
            box.setLayout(box_layout)

            for name, value in meta_args.items():
                try:
                    inspector_option = meta_arg_data[name]

                # This happens with hidden args passed to factory (currently only exists for meta args
                # [hive.pull/push in/out])
                # Hidden args means that the inspector didn't find these args, but they were passed in the args dict
                except KeyError:
                    continue

                widget, controller = create_widget(inspector_option.data_type, inspector_option.options)
                widget.setEnabled(False)
                controller.value = value

                box_layout.addRow(self.tr(name), widget)

            edit_button = QPushButton('Re-configure')
            edit_button.setToolTip("Re-create this node with new meta-args, and attempt to preserve state")

            edit_button.clicked.connect(lambda: self.do_morph_node.emit(node))

            box_layout.addRow(edit_button)

        # Args
        for wrapper_name, title_name in (("args", "Builder Args"), ("cls_args", "Class Args")):
            try:
                args = node.params[wrapper_name]
            except KeyError:
                continue

            arg_data = node.params_info[wrapper_name]

            # Create container
            box = QFrame()
            layout.addRow(self.tr(title_name), box)

            box.setFrameShape(QFrame.StyledPanel)
            box_layout = QFormLayout()
            box.setLayout(box_layout)

            for name, value in args.items():
                # Get data type
                inspector_option = arg_data[name]

                widget, controller = create_widget(inspector_option.data_type, inspector_option.options)
                widget.controller = controller

                def on_changed(value, name=name, wrapper_name=wrapper_name):
                    self.set_param_value.emit(node, wrapper_name, name, value)

                controller.value = value
                controller.on_changed.subscribe(on_changed)

                box_layout.addRow(self.tr(name), widget)


class ConfigurationPanel(ArgumentsPanel):
    rename_node = pyqtSignal(object, str)
    on_import_path_clicked = pyqtSignal(str)

    def _update_layout(self, node):
        layout = self._layout

        widget = QClickableLabel(node.import_path)
        widget.clicked.connect(partial(self.on_import_path_clicked.emit, node.import_path))

        widget.setStyleSheet("QLabel {text-decoration: underline; color:#858585; }")
        layout.addRow(self.tr("Import path"), widget)

        widget = QLineEdit()
        widget.setPlaceholderText(node.name)
        widget.textChanged.connect(partial(self.rename_node.emit, node))
        layout.addRow(self.tr("&Name"), widget)

        super()._update_layout(node)


class FoldingPanel(NodeContextPanelBase):
    fold_pin = pyqtSignal(object)
    unfold_pin = pyqtSignal(object)

    # For nested configurations
    do_morph_node = pyqtSignal(object)
    set_param_value = pyqtSignal(object, str, str, object)

    def _fold_antenna(self, pin):
        self.fold_pin.emit(pin)
        self.on_node_updated(pin.node)

    def _unfold_antenna(self, pin):
        self.unfold_pin.emit(pin)
        self.on_node_updated(pin.node)

    def _update_layout(self, node):
        layout = self._layout

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

                # Display inline configuration of folded pin
                widget = ArgumentsPanel()
                widget.set_param_value.connect(self.set_param_value)
                widget.do_morph_node.connect(self.do_morph_node)

                # Find folded node
                target_connection = next(iter(pin.connections))
                target_pin = target_connection.output_pin
                widget.node = target_pin.node

                layout.addWidget(widget)

            else:
                continue
