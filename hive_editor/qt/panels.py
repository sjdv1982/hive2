from functools import partial

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QFrame, QLineEdit, QPushButton, QScrollArea

from .label import ClickableLabelWidget
from .utils import create_widget


# TODO fix scrolling
class NodeContextPanelBase(QWidget):

    def __init__(self, parent=None):
        super(NodeContextPanelBase, self).__init__(parent)

        self._node = None
        self._layout = QFormLayout()

        self._widget = QWidget()
        self._widget.setLayout(self._layout)

        self._scrollWidget = QScrollArea()
        self._scrollWidget.setWidgetResizable(True)
        self._scrollWidget.setWidget(self._widget)

        self._mainLayout = QVBoxLayout()
        self._mainLayout.addWidget(self._scrollWidget)
        self.setLayout(self._mainLayout)

    def node(self):
        return self._node

    def setNode(self, node):
        self._node = node
        self._onNodeUpdated(node)

    def _clearLayout(self):
        layout = self._layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def _updateLayout(self, node):
        raise NotImplementedError

    def _onNodeUpdated(self, node):
        self._clearLayout()

        if node is None:
            return

        self._updateLayout(node)


class ArgumentsPanel(NodeContextPanelBase):
    doMorphNode = pyqtSignal(object)
    updateParam = pyqtSignal(object, str, str, object)

    def __init__(self, parent=None, show_meta=True, show_compact=False):
        self._show_meta = show_meta
        self._show_compact = show_compact

        super(ArgumentsPanel, self).__init__(parent)

    def _updateLayout(self, node):
        layout = self._layout

        # Meta Args
        meta_args = node.params.get('meta_args')
        if meta_args and self._show_meta:
            meta_arg_data = node.params_info["meta_args"]

            # Create container
            if self._show_compact:
                this_layout = layout

            else:
                box = QFrame()
                box.setFrameShape(QFrame.StyledPanel)
                this_layout = QFormLayout()
                box.setLayout(this_layout)
                layout.addRow(self.tr("Meta Args"), box)

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

                this_layout.addRow(self.tr(name), widget)

            edit_button = QPushButton('Re-configure')
            edit_button.setToolTip("Re-create this node with new meta-args, and attempt to preserve state")

            edit_button.clicked.connect(lambda: self.doMorphNode.emit(node))

            this_layout.addRow(edit_button)

        # Args
        for wrapper_name, title_name in (("args", "Builder Args"), ("cls_args", "Class Args")):
            try:
                args = node.params[wrapper_name]
            except KeyError:
                continue

            arg_data = node.params_info[wrapper_name]

            # Create container
            if self._show_compact:
                this_layout = layout
            else:
                box = QFrame()
                box.setFrameShape(QFrame.StyledPanel)
                this_layout = QFormLayout()
                box.setLayout(this_layout)
                layout.addRow(self.tr(title_name), box)

            for name, value in args.items():
                # Get data type
                inspector_option = arg_data[name]

                widget, controller = create_widget(inspector_option.data_type, inspector_option.options)
                widget.controller = controller

                def on_changed(value, name=name, wrapper_name=wrapper_name):
                    self.updateParam.emit(node, wrapper_name, name, value)

                controller.value = value
                controller.on_changed.subscribe(on_changed)

                this_layout.addRow(self.tr(name), widget)


class ConfigurationPanel(ArgumentsPanel):
    doRenameNode = pyqtSignal(object, str)
    onReferencePathClicked = pyqtSignal(str)

    def _updateLayout(self, node):
        layout = self._layout

        widget = ClickableLabelWidget(node.reference_path)
        widget.setToolTip("Python module path + class name of Hive")
        widget.clicked.connect(partial(self.onReferencePathClicked.emit, node.reference_path))

        widget.setStyleSheet("QLabel {text-decoration: underline; color:#858585; }")
        layout.addRow(self.tr("Reference path"), widget)

        widget = QLineEdit()
        widget.setText(node.name)
        widget.textChanged.connect(partial(self.doRenameNode.emit, node))
        layout.addRow(self.tr("&Name"), widget)

        super(ConfigurationPanel, self)._updateLayout(node)


class FoldingPanel(NodeContextPanelBase):
    doFoldPin = pyqtSignal(object)
    doUnfoldPin = pyqtSignal(object)

    # For nested configurations
    doMorphNode = pyqtSignal(object)
    updateParam = pyqtSignal(object, str, str, object)

    def _foldAntenna(self, pin):
        self.doFoldPin.emit(pin)
        self._onNodeUpdated(pin.node)

    def _unfoldAntenna(self, pin):
        self.doUnfoldPin.emit(pin)
        self._onNodeUpdated(pin.node)

    def _updateLayout(self, node):
        layout = self._layout

        for name, pin in node.inputs.items():
            if pin.mode != "pull":
                continue

            if pin.is_foldable:
                button = QPushButton("Fol&d")
                button.setToolTip("Collapse pin (and connected node) into this node.\nCreate node for pin if no node exists")
                on_clicked = partial(self._foldAntenna, pin)

                layout.addRow(self.tr(name), button)
                button.clicked.connect(on_clicked)

            elif pin.is_folded:
                button = QPushButton("&Unfold")
                button.setToolTip("Expand pin (and connected node) out of this node.")
                on_clicked = partial(self._unfoldAntenna, pin)

                layout.addRow(self.tr(name), button)
                button.clicked.connect(on_clicked)

                # Display inline configuration of folded pin
                widget = ArgumentsPanel(show_meta=False, show_compact=True)
                widget.updateParam.connect(self.updateParam)
                widget.doMorphNode.connect(self.doMorphNode)

                # Find folded node
                target_connection = next(iter(pin.connections))
                target_pin = target_connection.output_pin
                widget.setNode(target_pin.node)

                layout.addWidget(widget)

            else:
                continue
