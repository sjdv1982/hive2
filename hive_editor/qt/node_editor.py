import os
from functools import partial
from webbrowser import open as open_url

from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QPoint
from PyQt5.QtGui import QIcon, QCursor, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, QPushButton, QMessageBox, QSplitter, QTextEdit, QHBoxLayout,
                             QHeaderView, QTableView, QListWidget, QListWidgetItem, QMenu, QMainWindow, QDockWidget,
                             QLabel)

from .console import ConsoleWidget
from .floating_text import FloatingTextWidget
from .configuration_dialogue import ConfigurationDialogue
from .node import QtNode
from .panels import FoldingPanel, ConfigurationPanel
from .tree import TreeWidget
from .utils import create_widget
from .view import NodeView, NodePreviewView

from ..code_generator import hivemap_to_python_source
from ..history import CommandLogManager
from ..inspector import InspectorOption
from ..utils import find_file_path_of_hive_path, import_module_from_hive_path
from ..node import MimicFlags, NodeTypes
from ..node_manager import NodeManager


class SourceCodePreviewDialogue(QDialog):

    def __init__(self, parent, code):
        QDialog.__init__(self, parent)
        self.resize(600, 500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        text_editor, controller = create_widget("str.code")
        controller.value = code

        self.setAttribute(Qt.WA_DeleteOnClose)
        layout.addWidget(text_editor)


class PreviewWidget(QWidget):
    doShowCode = pyqtSignal()

    def __init__(self, parent=None):
        super(PreviewWidget, self).__init__(parent)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._previewView = NodePreviewView()
        self._layout.addWidget(self._previewView)

        self._showSource = QPushButton("Show Source")
        self._showSource.setToolTip("Display Python source code to produce this Hive")
        self._layout.addWidget(self._showSource)
        self._showSource.clicked.connect(self.doShowCode)

    def updatePreview(self, nodes):
        from ..node import Node
        # Instead of creating a hive object and then using get_io_info, this is more lightweight
        preview_node = Node("<preview>", NodeTypes.HIVE, "<preview>", {}, {})

        for node_name, node in sorted(nodes.items()):
            # If an input IO bee
            if node.reference_path in {"hive.antenna", "hive.entry"}:
                pin = next(iter(node.outputs.values()))
                try:
                    connection = next(iter(pin.connections))

                except StopIteration:
                    continue

                remote_pin = connection.input_pin
                input_pin = preview_node.add_input(node_name, mimic_flags=MimicFlags.SHAPE | MimicFlags.COLOUR)
                input_pin.mimic_other_pin(remote_pin)

            # If an output IO bee
            if node.reference_path in {"hive.output", "hive.hook"}:
                pin = next(iter(node.inputs.values()))
                try:
                    connection = next(iter(pin.connections))

                except StopIteration:
                    continue

                remote_pin = connection.output_pin
                output_pin = preview_node.add_output(node_name, mimic_flags=MimicFlags.SHAPE | MimicFlags.COLOUR)
                output_pin.mimic_other_pin(remote_pin)

        self._previewView.previewNode(preview_node)


class DebugControlWidget(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        next_button = QPushButton()
        next_button.setToolTip("Step")

        icon = QIcon()
        file_path = os.path.join(os.path.dirname(__file__), "svg/radio_checked.svg")
        icon.addFile(file_path)

        next_button.setIcon(icon)

        self._layout.addWidget(next_button)
        next_button.pressed.connect(self.parent()._skipActiveBreakpoint)


class DebugWidget(QWidget):
    onSkipBreakpoint = pyqtSignal(str)

    def __init__(self, max_history_entries=15):
        QWidget.__init__(self)

        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        self._breakpointList = QListWidget(self)
        self._debugControls = DebugControlWidget(self)
        self._historyView = QTableView(self)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._debugControls)
        splitter.addWidget(self._breakpointList)
        splitter.addWidget(self._historyView)

        self._historyModel = QStandardItemModel(self._historyView)
        self._labels = ("Source Bee", "Target Bee", "Operation", "Value", "Index")
        self._historyModel.setHorizontalHeaderLabels(self._labels)

        # Apply the model to the list view
        self._historyView.setModel(self._historyModel)
        self._historyView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._layout.addWidget(splitter)

        self._textToItem = {}
        self._breakpointList.setEnabled(False)

        self._index = 0

        self._maxHistoryEntries = max_history_entries

    def _skipActiveBreakpoint(self):
        item = self._breakpointList.currentItem()
        if item is None:
            return

        breakpoint_name = item.text()
        self._breakpointList.setCurrentItem(None)

        self.onSkipBreakpoint.emit(breakpoint_name)

    def addBreakpoint(self, name):
        if name in self._textToItem:
            raise ValueError

        item = QListWidgetItem(name)
        self._breakpointList.addItem(item)

        icon = QIcon()
        file_path = os.path.join(os.path.dirname(__file__), "svg/radio_checked.svg")
        icon.addFile(file_path)

        item.setIcon(icon)
        self._textToItem[name] = item

    def setPendingBreakpoint(self, name):
        item = self._textToItem[name]
        self._breakpointList.setCurrentItem(item)

    def removeBreakpoint(self, name):
        item = self._textToItem.pop(name)
        row = self._breakpointList.row(item)
        self._breakpointList.takeItem(row)

    def logOperation(self, source_name, target_name, operation, value=""):
        index = self._index
        self._index += 1

        # Create an item with a caption
        row_items = QStandardItem(source_name), QStandardItem(target_name), QStandardItem(operation), \
                    QStandardItem(value), QStandardItem(str(index))

        # Add the item to the model
        self._historyModel.appendRow(row_items)

        if self._historyModel.rowCount() > self._maxHistoryEntries:
            self._historyModel.takeRow(0)

    def clearHistory(self):
        self._historyModel.clear()
        self._historyModel.setHorizontalHeaderLabels(self._labels)
        self._index = 0

    def clearBreakpoints(self):
        self._breakpointList.clear()
        self._textToItem.clear()


class NodeEditorSpace(QMainWindow):
    onSaveStateUpdated = pyqtSignal(bool)
    doOpenFile = pyqtSignal(str)
    onNodeContextMenu = pyqtSignal(object, object)
    onDroppedForParent = pyqtSignal(QEvent, QPoint)

    def __init__(self, file_path=None, project_path=None):
        super(NodeEditorSpace, self).__init__()

        self._filePath = file_path
        self._history = CommandLogManager()
        self._history.on_updated.subscribe(self._onHistoryUpdated)

        self._nodeManager = NodeManager(self._history)

        self._view = NodeView(self)

        self.setDockNestingEnabled(True)
        self.setCentralWidget(self._view)

        # Node manager to view
        node_manager = self._nodeManager
        node_manager.on_node_created.subscribe(self._onNodeCreated)
        node_manager.on_node_destroyed.subscribe(self._onNodeDestroyed)
        node_manager.on_node_moved.subscribe(self._onNodeMoved)
        node_manager.on_node_renamed.subscribe(self._onNodeRenamed)
        node_manager.on_connection_created.subscribe(self._onConnectionCreated)
        node_manager.on_connection_destroyed.subscribe(self._onConnectionDestroyed)
        node_manager.on_connection_reordered.subscribe(self._onConnectionReordered)
        node_manager.on_pin_folded.subscribe(self._onPinFolded)
        node_manager.on_pin_unfolded.subscribe(self._onPinUnfolded)

        self._historyID = self._history.command_id
        self._lastSavedID = self._historyID

        # View to node manager
        view = self._view
        view.onNodesMoved.connect(self._guiNodesMoved)
        view.onNodesDeleted.connect(self._guiNodesDestroyed)
        view.onConnectionCreated.connect(self._guiConnectionCreated)
        view.onConnectionsDestroyed.connect(self._guiConnectionsDestroyed)
        view.onConnectionReordered .connect(self._guiConnectionReordered)
        view.onNodeSelected.connect(self._guiNodeSelected)
        view.onNodeDeselectd.connect(self._guiNodeDeselected)
        view.onDropped.connect(self._guiOnDropped)
        view.onDragMove.connect(self._guiOnDragMove)
        view.onNodeRightClick.connect(self._guiNodeRightClicked)
        view.onSocketInteract.connect(self._guiSocketInteract)

        self._nodeToQtNode = {}
        self._connectionToQtConnection = {}

        self._docstringWidget = QTextEdit()
        self._docstringWidget.textChanged.connect(self._docstringTextUpdated)

        self._configurationWidget = ConfigurationPanel()
        self._configurationWidget.doMorphNode.connect(self._doPanelMorphNode)
        self._configurationWidget.onReferencePathClicked.connect(self._panelReferencePathClicked)
        self._configurationWidget.updateParam.connect(self._nodeManager.set_param_value)
        self._configurationWidget.doRenameNode.connect(self._nodeManager.rename_node)

        self._foldingWidget = FoldingPanel()
        self._foldingWidget.doMorphNode.connect(self._doPanelMorphNode)
        self._foldingWidget.updateParam.connect(self._nodeManager.set_param_value)
        self._foldingWidget.doFoldPin.connect(self._nodeManager.fold_pin)
        self._foldingWidget.doUnfoldPin.connect(self._nodeManager.unfold_pin)

        self._previewWidget = PreviewWidget()
        self._previewWidget.doShowCode.connect(self._previewShowCode)

        console_display_text = """
 Hive GUI console.

 Globals and useful attributes:
 ------------------------------------------------------------------
  editor                  - current node editor
  editor.debugController() - current debug controller if debugging
  editor.nodeManager()     - current internal node manager

 Note:
 ------------------------------------------------------------------
  The Qt namespace follows PyQt camelcase naming conventions
  The hive_editor/.../ namespace follows PEP8 naming conventions
"""
        self._consoleWidget = ConsoleWidget(local_dict=dict(editor=self), display_text=console_display_text)

        self._debugActiveWidget = DebugWidget()
        self._debugController = None
        self._debugBlinkTime = 0.1
        self._debugInactiveWidget = QLabel("No debugging session currently active")
        self._debugInactiveWidget.setAlignment(Qt.AlignCenter)

        self._hiveWidget = TreeWidget()
        self._beeWidget = TreeWidget()

        self._beeWindow = self._createSubwindow("Bees", "left", widget=self._beeWidget)
        self._hiveWindow = self._createSubwindow("Hives", "left", widget=self._hiveWidget)
        self._previewWindow = self._createSubwindow("Preview", "left", widget=self._previewWidget)
        self._debugWindow = self._createSubwindow("Debugging", "bottom", widget=self._debugInactiveWidget)
        self._consoleWindow = self._createSubwindow("Console", "bottom", widget=self._consoleWidget)
        self._configurationWindow = self._createSubwindow("Configuration", "right", widget=self._configurationWidget)
        self._foldingWindow = self._createSubwindow("Folding", "right", widget=self._foldingWidget)
        self._docstringWindow = self._createSubwindow("Docstring", "left", widget=self._docstringWidget)

        # Close breakpoints and console windows by default
        self._debugWindow.close()

        # Make tabs
        self.tabifyDockWidget(self._beeWindow, self._hiveWindow)
        self.tabifyDockWidget(self._docstringWindow, self._previewWindow)
        self.tabifyDockWidget(self._debugWindow, self._consoleWindow)

        self._projectPath = project_path
        self._pendingDroppedNodeInfo = None

        # Permitted MIME types to delegate to parent
        self._parentDropMimeTypes = set()

        if file_path is not None:
            self.load(file_path)

    def filePath(self):
        return self._filePath

    def setFilePath(self, file_path):
        self._filePath = file_path

    def hasUnsavedChanges(self):
        return self._lastSavedID != self._historyID

    def nodeManager(self):
        return self._nodeManager

    def isDebugging(self):
        return self._debugController is not None

    def projectPath(self):
        return self._projectPath

    def debugController(self):
        return self._debugController

    def parentDropMimeTypes(self):
        return self._parentDropMimeTypes

    def setParentDropMimeTypes(self, drop_types):
        self._parentDropMimeTypes = drop_types

    def _consumeDroppedNodeInfo(self):
        info, self._pendingDroppedNodeInfo = self._pendingDroppedNodeInfo, None
        if info is None:
            raise ValueError("Nothing to drop!")
        return info

    def _onSelectedTreeNode(self, path, node_type):
        self._pendingDroppedNodeInfo = path, node_type

    def _createSubwindow(self, title, position, closeable=True, widget=None):
        area_classes = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea,
        }
        area = area_classes[position]

        window = QDockWidget(title, self)
        features = QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable
        if closeable:
            features |= QDockWidget.DockWidgetClosable

        window.setFeatures(features)

        if widget is not None:
            window.setWidget(widget)

        self.addDockWidget(area, window)

        return window

    def _previewShowCode(self):
        """Show hivemap code in dialogue window"""
        hivemap = self._nodeManager.to_hivemap()
        code = hivemap_to_python_source(hivemap, class_name='PreviewHive')
        dialogue = SourceCodePreviewDialogue(self, code)
        dialogue.show()

    def _doPanelMorphNode(self, node):
        inspector = self._nodeManager.get_inspector_for(node.node_type)
        inspection_generator = inspector.inspect(node.reference_path)

        params = self._displayModalInspector(inspection_generator)
        self._nodeManager.morph_node(node, params)

    def _panelReferencePathClicked(self, reference_path):
        module, class_name = import_module_from_hive_path(reference_path)
        open_url(module.__file__)

    def _pinToBeeContainerName(self, pin):
        return "{}.{}".format(pin.node.name, pin.name)

    def onDebuggingStarted(self, controller):
        if self.hasUnsavedChanges():
            reply = QMessageBox.warning(self, 'Revert Changes', "This file has unsaved changes, and a debugger has been launched. Do you want to reset them?",
                                        QMessageBox.Yes, QMessageBox.No)

            if reply != QMessageBox.Yes:
                controller.close()
                return

            self.load()

        self._debugController = controller
        self._debugWindow.setWidget(self._debugActiveWidget)

        controller.on_push_out.subscribe(lambda source_name, target_name, value:
                                               self._onDebugOperation(source_name, target_name,
                                                                      operation="push-out", value=value))
        controller.on_pull_in.subscribe(lambda source_name, target_name, value:
                                              self._onDebugOperation(source_name, target_name,
                                                                     operation="pull-in", value=value))
        controller.on_trigger.subscribe(partial(self._onDebugOperation, operation="trigger"))
        controller.on_pre_trigger.subscribe(partial(self._onDebugOperation, operation="pre-trigger"))
        controller.on_breakpoint_hit.subscribe(self._debugActiveWidget.setPendingBreakpoint)
        controller.on_breakpoint_added.subscribe(self._onBreakpointAdded)
        controller.on_breakpoint_removed.subscribe(self._onBreakpointRemoved)

        self._debugActiveWidget.onSkipBreakpoint.connect(controller.skip_breakpoint)

    def onDebuggingFinished(self):
        debug_controller = self._debugController

        debug_controller.on_push_out.clear()
        debug_controller.on_pull_in.clear()
        debug_controller.on_trigger.clear()
        debug_controller.on_pre_trigger.clear()
        debug_controller.on_breakpoint_added.clear()
        debug_controller.on_breakpoint_removed.clear()
        debug_controller.on_breakpoint_hit.clear()

        self._debugController = None

        # Reset debug widget
        self._debugActiveWidget.clearHistory()
        self._debugActiveWidget.clearBreakpoints()
        self._debugActiveWidget.onSkipBreakpoint.disconnect()

        self._debugWindow.setWidget(self._debugInactiveWidget)

    def _onDebugOperation(self, source_name, target_name, operation, value=None):
        self._debugActiveWidget.logOperation(source_name, target_name, operation, value)

        source_node_name, source_pin_name = source_name.split(".")
        target_node_name, target_pin_name = target_name.split(".")

        source_node = self._node_manager.nodes[source_node_name]
        target_node = self._node_manager.nodes[target_node_name]

        source_pin = source_node.outputs[source_pin_name]
        target_pin = target_node.inputs[target_pin_name]

        connection = next(c for c in source_pin.connections if c.input_pin is target_pin)
        gui_connection = self._connectionToQtConnection[connection]

        self._view.blinkConnection(gui_connection, self._debugBlinkTime)

    def _onHistoryUpdated(self, command_id):
        self._historyID = command_id

        has_unsaved_changes = self.hasUnsavedChanges()

        # Stop debugging if history is updated!
        if has_unsaved_changes and self.isDebugging():
            self.load()
            self._debugController.close()

        else:
            self.onSaveStateUpdated.emit(has_unsaved_changes)

        self._previewWidget.updatePreview(self._nodeManager.nodes)

    def _onNodeCreated(self, node):
        gui_node = QtNode(node, self._view)
        print("CREATED")

        self._nodeToQtNode[node] = gui_node
        self._view.addNode(gui_node)

        # Default select added node
        if not self._view.guiSelectedNodes():
            gui_node.setSelected(True)

    def _onNodeDestroyed(self, node):
        gui_node = self._nodeToQtNode.pop(node)
        gui_node.onDeleted()

        self._view.removeNode(gui_node)

    def _onBreakpointAdded(self, bee_container_name):
        self._debugActiveWidget.addBreakpoint(bee_container_name)

        node_name, pin_name = bee_container_name.split('.')
        node = self._node_manager.nodes[node_name]

        gui_node = self._nodeToQtNode[node]
        socket_row = gui_node.getSocketRow(pin_name)

        self._view.enableSocketDebugging(gui_node, socket_row)

    def _onBreakpointRemoved(self, bee_container_name):
        self._debugActiveWidget.removeBreakpoint(bee_container_name)

        # Visual
        node_name, pin_name = bee_container_name.split('.')
        node = self._node_manager.nodes[node_name]

        gui_node = self._nodeToQtNode[node]
        socket_row = gui_node.getSocketRow(pin_name)

        self._view.disableSocketDebugging(gui_node, socket_row)

    def _onNodeMoved(self, node, position):
        gui_node = self._nodeToQtNode[node]

        self._view.setNodePosition(gui_node, position)

    def _onNodeRenamed(self, node, name):
        gui_node = self._nodeToQtNode[node]
        self._view.setNodeName(gui_node, name)

    def _onConnectionCreated(self, connection):
        output_pin = connection.output_pin
        input_pin = connection.input_pin

        # Update all socket rows colours for each pin's GUI node
        input_gui_node = self._nodeToQtNode[input_pin.node]
        output_gui_node = self._nodeToQtNode[output_pin.node]

        input_gui_node.refreshSocketRows()
        output_gui_node.refreshSocketRows()

        # Get sockets for involved pins
        output_socket = self._findSocketFromPin(output_pin)
        input_socket = self._findSocketFromPin(input_pin)

        # Create connection
        from .connection import Connection

        # Choose pin for styling info
        if output_pin.mode == "any":
            style_pin = input_pin
        else:
            style_pin = output_pin

        # Use dot style for virtual relationships
        if output_pin.is_virtual or input_pin.is_virtual:
            style = "dot"

        else:
            style = "dashed" if style_pin.mode == "pull" else "solid"

        curve = True

        gui_connection = Connection(output_socket, input_socket, style=style, curve=curve)
        self._connectionToQtConnection[connection] = gui_connection

        # Push connections have ordering
        if style_pin.mode == "push":
            widget = FloatingTextWidget(gui_connection)
            widget.setVisible(False)
            gui_connection.setCenterWidget(widget)

        gui_connection.updatePath()

        # Update preview
        self._view.addConnection(gui_connection)

    def _onConnectionDestroyed(self, connection):
        # Remove connection
        gui_connection = self._connectionToQtConnection.pop(connection)
        self._view.removeConnection(gui_connection)

        # Inform connection it has been deleted
        gui_connection.onDeleted()

        # Update connection indices of other connections
        output_pin = connection.output_pin
        for i, other_connection in enumerate(output_pin.connections):
            other_gui_connection = self._connectionToQtConnection[other_connection]
            self._view.reorderConnection(other_gui_connection, i)

    def _onConnectionReordered(self, connection, index):
        gui_connection = self._connectionToQtConnection[connection]
        self._view.reorderConnection(gui_connection, index)

    def _onPinFolded(self, pin):
        # Get node
        node = pin.node
        gui_node = self._nodeToQtNode[node]

        # Get socket
        socket_row = gui_node.getSocketRow(pin.name)

        # Get target
        target_connection = next(iter(pin.connections))
        target_pin = target_connection.output_pin
        target_node = target_pin.node

        target_gui_node = self._nodeToQtNode[target_node]
        self._view.foldNode(socket_row, target_gui_node)

    def _onPinUnfolded(self, pin):
        # Get node
        node = pin.node
        gui_node = self._nodeToQtNode[node]

        # Get socket
        socket_row = gui_node.getSocketRow(pin.name)

        # Get target
        target_connection = next(iter(pin.connections))
        target_pin = target_connection.output_pin
        target_node = target_pin.node

        target_gui_node = self._nodeToQtNode[target_node]
        self._view.unfoldNode(socket_row, target_gui_node)

    # GUI nodes
    def _guiOnDragMove(self, event):
        mime_data = event.mimeData()
        formats = mime_data.formats()

        if 'application/x-qabstractitemmodeldatalist' in formats:
            event.accept()

        elif self._parentDropMimeTypes.intersection(formats):
            event.accept()

        else:
            event.ignore()

    def _guiOnDropped(self, event, pos):
        mime_data = event.mimeData()
        formats = mime_data.formats()

        if 'application/x-qabstractitemmodeldatalist' in formats:
            self.addNodeAt(pos, *self._consumeDroppedNodeInfo())

        elif self._parentDropMimeTypes.intersection(formats):
            self.onDroppedForParent.emit(event, pos)

    def _guiConnectionCreated(self, start_socket, end_socket):
        start_pin = start_socket.parentSocketRow().pin()
        end_pin = end_socket.parentSocketRow().pin()
        self._nodeManager.create_connection(start_pin, end_pin)

    def _guiConnectionsDestroyed(self, gui_connections):
        gui_to_connection = {gui_c: c for c, gui_c in self._connectionToQtConnection.items()}
        connections = [gui_to_connection[gui_c] for gui_c in gui_connections]
        self._nodeManager.delete_connections(connections)

    def _guiConnectionReordered(self, gui_connection, index):
        connection = next(c for c, gui_c in self._connectionToQtConnection.items() if gui_c is gui_connection)
        self._nodeManager.reorder_connection(connection, index)

    def _guiNodeSelected(self, gui_node):
        node = gui_node.node()

        self._foldingWidget.setNode(node)
        self._configurationWidget.setNode(node)

    def _guiNodeDeselected(self):
        self._foldingWidget.setNode(None)
        self._configurationWidget.setNode(None)

    def _guiSocketInteract(self, gui_socket):
        debug_controller = self._debugController
        if debug_controller is None:
            return

        pin = gui_socket.parentSocketRow().pin()
        bee_container_name = self._pinToBeeContainerName(pin)

        if bee_container_name not in debug_controller.breakpoints:
            debug_controller.addBreakpoint(bee_container_name)

        else:
            debug_controller.removeBreakpoint(bee_container_name)

    def _guiNodeRightClicked(self, gui_node, event):
        node = gui_node.node()
        self._guiHiveEdit(node.reference_path, event.screenPos())

    def _guiTreeHiveEdit(self, reference_path, event):
        self._guiHiveEdit(reference_path, event.globalPos())

    def _guiHiveEdit(self, reference_path, global_pos):
        # Can only edit .hivemaps
        try:
            hivemap_file_path = find_file_path_of_hive_path(reference_path)

        except ValueError:
            return

        menu = QMenu(self)
        edit_action = menu.addAction("Edit Hivemap")
        called_action = menu.exec_(global_pos)

        if called_action != edit_action:
            return

        self.doOpenFile.emit(hivemap_file_path)

    def _guiNodesDestroyed(self, gui_nodes):
        nodes = [gui_node.node() for gui_node in gui_nodes]
        self._nodeManager.delete_nodes(nodes)

    def _guiNodesMoved(self, gui_nodes):
        node_to_position = {gui_node.node(): (gui_node.pos().x(), gui_node.pos().y()) for gui_node in gui_nodes}
        self._nodeManager.reposition_nodes(node_to_position)

    def _findSocketFromPin(self, pin):
        gui_node = self._nodeToQtNode[pin.node]
        socket_row = gui_node.getSocketRow(pin.name)
        return socket_row.socket()

    def _docstringTextUpdated(self):
        self._nodeManager.docstring = self._docstringWidget.toPlainText()

    def _displayModalInspector(self, inspector):
        """Step through inspector with configuration via a modal dialogue

        :param inspector: inspector to process
        """
        params = {}

        previous_values = None
        while True:
            try:
                stage_name, stage_options = inspector.send(previous_values)

            except StopIteration:
                break

            dialogue = ConfigurationDialogue()
            dialogue.setAttribute(Qt.WA_DeleteOnClose)
            dialogue.setWindowTitle(stage_name.replace("_", " ").title())

            for name, option in stage_options.items():
                # Get default
                default = option.default
                if default is InspectorOption.NoValue:
                    default = ConfigurationDialogue.NoValue

                # Allow textarea
                dialogue.addWidget(name, option.data_type, default, option.options)

            dialogue_result = dialogue.exec_()
            if dialogue_result == QDialog.Rejected:
                raise ConfigurationDialogue.DialogueCancelled("Menu cancelled")

            # Set result
            params[stage_name] = previous_values = dialogue.values

        return params

    def _checkForCyclicReferences(self, file_path):
        node_manager = self._nodeManager

        # Check that we aren't attempting to save-as a hivemap of an existing Node instance
        if not os.path.exists(file_path):
            return False

        for node in node_manager.nodes.values():
            # If destination file is a hivemap, don't allow
            try:
                hivemap_file_path = find_file_path_of_hive_path(node.reference_path)

            except ValueError:
                continue

            if file_path == hivemap_file_path:
                return True

        return False

    def addNodeAt(self, position, reference_path, node_type):
        inspection_generator = self._nodeManager.get_inspector_for(node_type).inspect(reference_path)

        if node_type == NodeTypes.HIVE:
            # Check Hive's hivemap isn't currently open
            if self._filePath is not None:
                # Check we don't have a source file
                try:
                    hivemap_file_path = find_file_path_of_hive_path(reference_path)

                except ValueError:
                    pass

                else:
                    if hivemap_file_path == self._filePath:
                        QMessageBox.critical(self, 'Cyclic Hive', "This Hive Node cannot be added to its own hivemap")
                        return

        params = self._displayModalInspector(inspection_generator)
        node = self._nodeManager.create_node(node_type, reference_path, params=params)

        view_position = self._view.mapFromGlobal(position)
        scene_position = self._view.mapToScene(view_position)
        pos = scene_position.x(), scene_position.y()

        self._nodeManager.reposition_node(node, pos)

    def addNodeAtMouse(self, reference_path, node_type):
        # Get mouse position
        cursor = QCursor()
        q_position = cursor.pos()
        self.addNodeAt(q_position, reference_path, node_type)

    def selectAll(self):
        self._view.selectAll()

    def undo(self):
        self._nodeManager.history.undo()

    def redo(self):
        self._nodeManager.history.redo()

    def cut(self):
        gui_nodes = self._view.guiSelectedNodes()
        nodes = [n.node() for n in gui_nodes]
        return self._nodeManager.cut(nodes)

    def copy(self):
        gui_nodes = self._view.guiSelectedNodes()
        nodes = [n.node() for n in gui_nodes]
        return self._nodeManager.copy(nodes)

    def paste(self, hivemap):
        self._nodeManager.paste(hivemap, self._view.mouse_pos)

    def save(self, file_path=None):
        if file_path is None:
            file_path = self._filePath

            if file_path is None:
                raise ValueError("Untitled hivemap cannot be saved without filename")

        if self._checkForCyclicReferences(file_path):
            QMessageBox.critical(self, 'Cyclic Hive', "Cannot save the Hivemap of a Hive node already instanced in this"
                                                      "editor")
            raise ValueError("Cyclic references cannot be saved to hivemap")

        # Export data
        data = self._nodeManager.to_string()
        with open(file_path, "w") as f:
            f.write(data)

        # Mark pending changes as false
        self._lastSavedID = self._historyID
        self.onSaveStateUpdated.emit(False)

    def load(self, file_path=None):
        if file_path is None:
            file_path = self._filePath

            if file_path is None:
                raise ValueError("Untitled hivemap cannot be loaded without filename")

        with open(file_path, 'r') as f:
            data = f.read()

        node_manager = self._nodeManager

        try:
            node_manager.load_string(data)

        except Exception as err:
            print("Error during loading")
            import traceback
            print(traceback.format_exc())
            return

        self._filePath = file_path

        # Mark pending changes as false
        self._lastSavedID = self._historyID

        self._view.frameSceneContent()
        self._docstringWidget.setPlainText(node_manager.docstring)

    def loadFromText(self, text):
        self._nodeManager.load_string(text)

    def updateHiveTree(self, hives):
        self._hiveWidget.setItems(hives)

        self._hiveWidget.onSelected.connect(partial(self._onSelectedTreeNode, node_type=NodeTypes.HIVE))
        self._hiveWindow.setWidget(self._hiveWidget)
        self._hiveWidget.onRightClick.connect(self._guiTreeHiveEdit)

    def updateBeeTree(self, bees):
        self._beeWidget.setItems(bees)
        self._beeWidget.onSelected.connect(partial(self._onSelectedTreeNode, node_type=NodeTypes.BEE))
        self._beeWindow.setWidget(self._beeWidget)

    def onEnter(self):
        # Set visibility
        self._debugActiveWidget.setVisible(self.isDebugging())

    def onExit(self):
        pass
