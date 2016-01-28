import os

from .console import QConsole
from .floating_text import FloatingTextWidget
from .panels import FoldingPanel, ConfigurationPanel, ArgsPanel
from .qt_core import *
from .qt_gui import *
from .utils import create_widget
from .view import NodeView, NodePreviewView
from ..code_generator import hivemap_to_builder_body
from ..inspector import InspectorOption
from ..node import Node, MimicFlags, NodeTypes
from ..node_manager import NodeManager


class DynamicInputDialogue(QDialog):

    class NoValue:
        pass

    class DialogueCancelled(Exception):
        pass

    def __init__(self, parent):
        QDialog.__init__(self, parent)

        buttons_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        buttons_box.accepted.connect(self.accept)
        buttons_box.rejected.connect(self.reject)

        self.form_group_box = QGroupBox("Form layout")

        self.layout = QFormLayout()
        self.form_group_box.setLayout(self.layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.form_group_box)
        main_layout.addWidget(buttons_box)

        self.setLayout(main_layout)

        self.value_getters = {}
        self.values = {}

    def add_widget(self, name, data_type=None, default=NoValue, options=None):
        widget, controller = create_widget(data_type, options)

        if default is not self.__class__.NoValue:
            try:
                controller.value = default

            except Exception as err:
                print(err)

        self.layout.addRow(QLabel(name), widget)
        self.value_getters[name] = controller.getter

    def accept(self):
        QDialog.accept(self)

        self.values = {n: v() for n, v in self.value_getters.items()}


class SourceCodePreviewDialogue(QDialog):

    def __init__(self, parent, code):
        QDialog.__init__(self, parent)
        self.resize(400, 500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        text_editor = QTextEdit()
        text_editor.setCurrentFont(QFont("Consolas"))
        text_editor.setPlainText(code)

        layout.addWidget(text_editor)


class PreviewWidget(QWidget):

    def __init__(self, node_manager):
        QWidget.__init__(self)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._preview_view = NodePreviewView()
        self._layout.addWidget(self._preview_view)

        self._node_manager = node_manager
        self._show_source = QPushButton("Show Source")
        self._layout.addWidget(self._show_source)
        self._show_source.clicked.connect(self._show_code)

    def _show_code(self):
        hivemap = self._node_manager.to_hivemap()
        code = hivemap_to_builder_body(hivemap)
        dialogue = SourceCodePreviewDialogue(self, code)
        dialogue.setAttribute(Qt.WA_DeleteOnClose)
        dialogue.show()

    def update_preview(self):
        # Instead of creating a hive object and then using get_io_info, this is more lightweight
        preview_node = Node("<preview>", NodeTypes.HIVE, "<preview>", {}, {})

        for node_name, node in sorted(self._node_manager.nodes.items()):
            # If an input IO bee
            if node.import_path in {"hive.antenna", "hive.entry"}:
                pin = next(iter(node.outputs.values()))
                try:
                    connection = next(iter(pin.connections))

                except StopIteration:
                    continue

                remote_pin = connection.input_pin
                input_pin = preview_node.add_input(node_name, mimic_flags=MimicFlags.SHAPE | MimicFlags.COLOUR)
                input_pin.mimic_other_pin(remote_pin)

            # If an output IO bee
            if node.import_path in {"hive.output", "hive.hook"}:
                pin = next(iter(node.inputs.values()))
                try:
                    connection = next(iter(pin.connections))

                except StopIteration:
                    continue

                remote_pin = connection.output_pin
                output_pin = preview_node.add_output(node_name, mimic_flags=MimicFlags.SHAPE | MimicFlags.COLOUR)
                output_pin.mimic_other_pin(remote_pin)

        self._preview_view.preview_node(preview_node)


class NodeEditorSpace(QWidget):

    def __init__(self, file_name=None):
        QWidget.__init__(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.file_name = file_name

        self._node_manager = NodeManager()

        self._view = NodeView(self)
        layout.addWidget(self._view)

        self._view.setParent(self)
        self._view.show()

        # Node manager to view
        nm = self._node_manager
        nm.on_node_created = self._on_node_created
        nm.on_node_destroyed = self._on_node_destroyed
        nm.on_node_moved = self._on_node_moved
        nm.on_node_renamed = self._on_node_renamed
        nm.on_connection_created = self._on_connection_created
        nm.on_connection_destroyed = self._on_connection_destroyed
        nm.on_connection_reordered = self._on_connection_reordered
        nm.on_pin_folded = self._on_pin_folded
        nm.on_pin_unfolded = self._on_pin_unfolded
        nm.history.on_updated = self._on_node_history_update

        self._history_id = None
        self._last_saved_id = None
        self.on_update_is_saved = None

        self.do_open_file = None
        self.get_dropped_node_info = None
        self.get_project_directory = None

        # View to node manager
        view = self._view
        view.on_nodes_moved = self._gui_nodes_moved
        view.on_nodes_deleted = self._gui_nodes_destroyed
        view.on_connection_created = self._gui_connection_created
        view.on_connections_destroyed = self._gui_connections_destroyed
        view.on_connection_reordered = self._gui_connection_reordered
        view.on_node_selected = self._gui_node_selected
        view.on_dropped = self._gui_on_dropped_node
        view.on_node_right_click = self._gui_node_right_clicked

        self._node_to_qt_node = {}
        self._connection_to_qt_connection = {}

        self._docstring_widget = QTextEdit()
        self._docstring_widget.textChanged.connect(self._docstring_text_updated)
        self._args_widget = ArgsPanel(self._node_manager)
        self._configuration_widget = ConfigurationPanel(self._node_manager)
        self._folding_widget = FoldingPanel(self._node_manager)
        self._preview_widget = PreviewWidget(self._node_manager)

        self._console_widget = QConsole(local_dict=dict(editor=self))

        if file_name is not None:
            self.load(file_name)

    @property
    def has_unsaved_changes(self):
        return self._last_saved_id != self._history_id

    @property
    def node_manager(self):
        return self._node_manager

    def _on_node_history_update(self, history):
        self._history_id = history.operation_id

        if callable(self.on_update_is_saved):
            self.on_update_is_saved(self.has_unsaved_changes)

    def _on_node_created(self, node):
        from .node import Node

        gui_node = Node(node, self._view)
        self._node_to_qt_node[node] = gui_node

        self._view.add_node(gui_node)

        # Update preview
        self._preview_widget.update_preview()

    def _on_node_destroyed(self, node):
        gui_node = self._node_to_qt_node[node]
        gui_node.on_deleted()

        self._view.remove_node(gui_node)

    def _on_node_moved(self, node, position):
        gui_node = self._node_to_qt_node[node]

        self._view.set_node_position(gui_node, position)

    def _on_node_renamed(self, node, name):
        gui_node = self._node_to_qt_node[node]
        self._view.set_node_name(gui_node, name)

        self._preview_widget.update_preview()

    def _on_connection_created(self, connection):
        output_pin = connection.output_pin
        input_pin = connection.input_pin

        # Update all socket rows colours for each pin's GUI node
        input_gui_node = self._node_to_qt_node[input_pin.node]
        output_gui_node = self._node_to_qt_node[output_pin.node]

        input_gui_node.refresh_socket_rows()
        output_gui_node.refresh_socket_rows()

        # Get sockets for involved pins
        output_socket = self._socket_from_pin(output_pin)
        input_socket = self._socket_from_pin(input_pin)

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
        self._connection_to_qt_connection[connection] = gui_connection

        # Push connections have ordering
        if style_pin.mode == "push":
            gui_connection._center_widget = widget = FloatingTextWidget(gui_connection)
            widget.setVisible(False)

        gui_connection.update_path()

        # Update preview
        self._view.add_connection(gui_connection)

        self._preview_widget.update_preview()

    def _on_connection_destroyed(self, connection):
        # Update preview
        gui_connection = self._connection_to_qt_connection.pop(connection)
        self._view.remove_connection(gui_connection)

        gui_connection.on_deleted()

        self._preview_widget.update_preview()

    def _on_connection_reordered(self, connection, index):
        gui_connection = self._connection_to_qt_connection[connection]
        self._view.reorder_connection(gui_connection, index)

        self._preview_widget.update_preview()

    def _on_pin_folded(self, pin):
        # Get node
        node = pin.node
        gui_node = self._node_to_qt_node[node]

        # Get socket
        socket_row = gui_node.get_socket_row(pin.name)

        # Get target
        target_connection = next(iter(pin.connections))
        target_pin = target_connection.output_pin
        target_node = target_pin.node

        target_gui_node = self._node_to_qt_node[target_node]
        self._view.fold_pin(socket_row, target_gui_node)

    def _on_pin_unfolded(self, pin):
        # Get node
        node = pin.node
        gui_node = self._node_to_qt_node[node]

        # Get socket
        socket_row = gui_node.get_socket_row(pin.name)

        # Get target
        target_connection = next(iter(pin.connections))
        target_pin = target_connection.output_pin
        target_node = target_pin.node

        target_gui_node = self._node_to_qt_node[target_node]
        self._view.unfold_pin(socket_row, target_gui_node)

    # GUI nodes
    def _gui_connection_created(self, start_socket, end_socket):
        start_pin = start_socket.parent_socket_row.pin
        end_pin = end_socket.parent_socket_row.pin
        self._node_manager.create_connection(start_pin, end_pin)

    def _gui_connections_destroyed(self, gui_connections):
        gui_to_connection = {gui_c: c for c, gui_c in self._connection_to_qt_connection.items()}
        connections = [gui_to_connection[gui_c] for gui_c in gui_connections]
        self._node_manager.delete_connections(connections)

    def _gui_connection_reordered(self, gui_connection, index):
        connection = next(c for c, gui_c in self._connection_to_qt_connection.items() if gui_c is gui_connection)
        self._node_manager.reorder_connection(connection, index)

    def _gui_node_selected(self, gui_node):
        if gui_node is None:
            node = None

        else:
            node = gui_node.node

        self._folding_widget.node = node
        self._configuration_widget.node = node
        self._args_widget.node = node

    def _gui_node_right_clicked(self, gui_node, event):
        node = gui_node.node

        if not callable(self.get_hivemap_path):
            return

        # Can only edit .hivemaps
        try:
            hivemap_file_path = self.get_hivemap_path(node.import_path)

        except ValueError:
            return

        menu = QMenu(self)
        edit_hivemap_action = menu.addAction("Edit Hivemap")

        action = menu.exec_(event.screenPos())

        if action != edit_hivemap_action:
            return

        if not callable(self.do_open_file):
            return

        self.do_open_file(hivemap_file_path)

    def _gui_nodes_destroyed(self, gui_nodes):
        nodes = [gui_node.node for gui_node in gui_nodes]
        self._node_manager.delete_nodes(nodes)

    def _gui_nodes_moved(self, gui_nodes):
        node_to_position = {gui_node.node: (gui_node.pos().x(), gui_node.pos().y()) for gui_node in gui_nodes}
        self._node_manager.reposition_nodes(node_to_position)

    def _gui_on_dropped_node(self, position):
        if not callable(self.get_dropped_node_info):
            return

        node_info = self.get_dropped_node_info()
        if node_info is None:
            return

        import_path, node_type = node_info
        self.add_node_at(position, import_path, node_type)

    def _socket_from_pin(self, pin):
        gui_node = self._node_to_qt_node[pin.node]
        socket_row = gui_node.get_socket_row(pin.name)
        return socket_row.socket

    def _docstring_text_updated(self):
        self._node_manager.docstring = self._docstring_widget.toPlainText()

    def _execute_inspector(self, inspector):
        params = {"meta_args": {}, "args": {}, "cls_args": {}}
        inspection_info = {"meta_args": {}, "args": {}, "cls_args": {}}

        previous_values = None
        while True:
            try:
                stage_name, stage_options = inspector.send(previous_values)

            except StopIteration:
                break

            dialogue = DynamicInputDialogue(self)
            dialogue.setAttribute(Qt.WA_DeleteOnClose)
            dialogue.setWindowTitle(stage_name.replace("_", " ").title())

            for name, option in stage_options.items():
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
            params[stage_name] = previous_values = dialogue.values

            # Save inspection stage
            inspection_info[stage_name] = stage_options

        return params

    def add_node_at(self, position, import_path, node_type):
        if node_type == NodeTypes.BEE:
            inspector = self._node_manager.bee_node_inspector.inspect(import_path)
            params = self._execute_inspector(inspector)
            node = self._node_manager.create_bee(import_path, params=params)

        else:
            # Check Hive's hivemap isn't currently open
            if self.file_name is not None:
                # Check we don't have a source file
                if callable(self.get_hivemap_path):
                    try:
                        hivemap_file_path = self.get_hivemap_path(import_path)

                    except ValueError:
                        pass

                    else:
                        if hivemap_file_path == self.file_name:
                            QMessageBox.critical(self, 'Cyclic Hive', "This Hive Node cannot be added to its own hivemap")
                            return

            inspector = self._node_manager.hive_node_inspector.inspect(import_path)
            params = self._execute_inspector(inspector)
            node = self._node_manager.create_hive(import_path, params=params)

        self._node_manager.reposition_node(node, position)

    def add_node_at_mouse(self, import_path, node_type):
        # Get mouse position
        cursor = QCursor()
        q_position = cursor.pos()
        q_position = self._view.mapFromGlobal(q_position)
        q_position = self._view.mapToScene(q_position)
        position = q_position.x(), q_position.y()

        self.add_node_at(position, import_path, node_type)

    def select_all(self):
        self._view.select_all()

    def undo(self):
        self._node_manager.history.undo()

    def redo(self):
        self._node_manager.history.redo()

    def cut(self):
        gui_nodes = self._view.gui_get_selected_nodes()
        nodes = [n.node for n in gui_nodes]
        return self._node_manager.cut(nodes)

    def copy(self):
        gui_nodes = self._view.gui_get_selected_nodes()
        nodes = [n.node for n in gui_nodes]
        return self._node_manager.copy(nodes)

    def paste(self, hivemap):
        self._node_manager.paste(hivemap, self._view.mouse_pos)

    def save(self, file_name=None):
        use_existing_file_name = file_name is None

        if use_existing_file_name:
            file_name = self.file_name

            if file_name is None:
                raise ValueError("Untitled hivemap cannot be saved without filename")

        node_manager = self._node_manager

        # Check that we aren't attempting to save-as a hivemap of an existing Node instance
        if os.path.exists(file_name) and callable(self.get_hivemap_path):
            for node in node_manager.nodes.values():
                # If destination file is a hivemap, don't allow
                try:
                    hivemap_source_path = self.get_hivemap_path(node.import_path)

                except ValueError:
                    continue

                if file_name == hivemap_source_path:
                    QMessageBox.critical(self, 'Cyclic Hive', "Cannot save the Hivemap of a Hive node already instanced"
                                                              "in this editor")
                    raise ValueError("Untitled hivemap cannot be saved without filename")

        # Export data
        data = node_manager.to_string()
        with open(file_name, "w") as f:
            f.write(data)

        self.file_name = file_name

        # Mark pending changes as false
        self._last_saved_id = self._history_id

        if callable(self.on_update_is_saved):
            self.on_update_is_saved(False)

    def load(self, file_name=None):
        if file_name is None:
            file_name = self.file_name

            if file_name is None:
                raise ValueError("Untitled hivemap cannot be loaded without filename")

        with open(file_name, 'r') as f:
            data = f.read()

        node_manager = self._node_manager

        try:
            node_manager.load_string(data)

        except Exception as err:
            print("Error during loading")
            import traceback
            print(traceback.format_exc())
            return

        self.file_name = file_name

        # Mark pending changes as false
        self._last_saved_id = self._history_id

        self._view.frame_scene_content()
        self._docstring_widget.setPlainText(node_manager.docstring)

    def on_enter(self, docstring_window, folding_window, configuration_window, parameter_window, preview_window,
                 console_window):
        docstring_window.setWidget(self._docstring_widget)
        folding_window.setWidget(self._folding_widget)
        configuration_window.setWidget(self._configuration_widget)
        parameter_window.setWidget(self._args_widget)
        preview_window.setWidget(self._preview_widget)
        console_window.setWidget(self._console_widget)

    def on_exit(self, docstring_window, folding_window, configuration_window, parameter_window, preview_window,
                console_window):
        docstring_window.setWidget(QWidget())
        folding_window.setWidget(QWidget())
        configuration_window.setWidget(QWidget())
        parameter_window.setWidget(QWidget())
        preview_window.setWidget(QWidget())
        console_window.setWidget(QWidget())
