from functools import partial
from webbrowser import open as open_url

from .gui_inspector import DynamicInputDialogue
from .label import QClickableLabel
from .qt_gui import *
from .qt_core import *
from .utils import create_widget
from ..inspector import InspectorOption
from ..utils import import_module_from_path


class NodeContextPanelBase(QWidget):

    def __init__(self, node_manager):
        QWidget.__init__(self)

        self._node = None

        self._layout = QFormLayout()
        self.setLayout(self._layout)

        self._node_manager = node_manager

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
    def _edit_meta_args(self, node):
        dialogue = DynamicInputDialogue(self)
        dialogue.setAttribute(Qt.WA_DeleteOnClose)
        dialogue.setWindowTitle("Meta Args")

        # Take inspection data
        existing_meta_args_view = node.params_info['meta_args']
        for name, option in existing_meta_args_view.items():
            # Get default
            default = option.default
            if default is InspectorOption.NoValue:
                default = DynamicInputDialogue.NoValue

            # Allow textarea
            dialogue.add_widget(name, option.data_type, default, option.options)

        dialogue_result = dialogue.exec_()
        if dialogue_result == QDialog.Rejected:
            raise DynamicInputDialogue.DialogueCancelled("Menu cancelled")

        # Set result
        meta_args = dialogue.values
        self._node_manager.morph_node(node, meta_args)

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

                # edit_button = QPushButton('Re-configure')
                # edit_button.setToolTip("Re-create this node with new meta-args, and attempt to preserve state")
                #
                # edit_callback = partial(self._edit_meta_args, node)
                # edit_button.clicked.connect(edit_callback)
                #
                # box_layout.addRow(edit_button)

        node_manager = self._node_manager

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

                def on_changed(value, name=name):
                    node_manager.set_param_value(node, "args", name, value)

                controller.value = value
                controller.on_changed.subscribe(on_changed)

                box_layout.addRow(self.tr(name), widget)


class ConfigurationPanel(ArgumentsPanel):

    def _rename_node(self, node, name):
        self._node_manager.rename_node(node, name)

    def _import_path_clicked(self, import_path):
        module, class_name = import_module_from_path(import_path)
        open_url(module.__file__)

    def _update_layout(self, node):
        layout = self._layout

        widget = QClickableLabel(node.import_path)
        widget.clicked.connect(partial(self._import_path_clicked, node.import_path))

        widget.setStyleSheet("QLabel {text-decoration: underline; color:#858585; }")
        layout.addRow(self.tr("Import path"), widget)

        widget = QLineEdit()
        widget.setPlaceholderText(node.name)
        widget.textChanged.connect(partial(self._rename_node, node))
        layout.addRow(self.tr("&Name"), widget)

        super()._update_layout(node)


class FoldingPanel(NodeContextPanelBase):

    def _fold_antenna(self, pin):
        self._node_manager.fold_pin(pin)
        self.on_node_updated(pin.node)

    def _unfold_antenna(self, pin):
        self._node_manager.unfold_pin(pin)
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

                widget = ArgumentsPanel(self._node_manager)

                target_connection = next(iter(pin.connections))
                target_pin = target_connection.output_pin
                widget.node = target_pin.node

                layout.addWidget(widget)

            else:
                continue
