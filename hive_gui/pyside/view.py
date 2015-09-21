# <license>
# Copyright (C) 2011 Andrea Interguglielmi, All rights reserved.
# This file is part of the coral repository downloaded from http://code.google.com/p/coral-repo.
#
# Modified for the Hive system by Sjoerd de Vries
# All modifications copyright (C) 2012 Sjoerd de Vries, All rights reserved
#
# Modified for the Hive2 system by Angus Hollands
# All modifications copyright (C) 2015 Angus Hollands, All rights reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# </license>

from __future__ import print_function, absolute_import

from PySide.QtCore import *
from PySide.QtGui import *

import functools

from .panels import FoldingPanel, ConfigurationPanel, ArgsPanel
from .utils import create_widget
from .scene import NodeUiScene

from ..node import NodeTypes
from ..node_manager import NodeManager
from ..inspector import InspectorOption
from ..gui_node_manager import IGUINodeManager
from ..utils import hivemap_to_builder_body


SELECT_SIZE = 10


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


class FloatingTextWidget(QGraphicsWidget):

    def __init__(self, parent=None, anchor="center"):
        QGraphicsWidget.__init__(self, parent)

        assert anchor in {"center", "corner"}
        self.anchor = anchor

        self._label = QGraphicsSimpleTextItem(self)
        self._label.setBrush(QColor(255, 255, 255))

        # Add dropshadow
        self._dropShadowEffect = QGraphicsDropShadowEffect()
        self.setGraphicsEffect(self._dropShadowEffect)

        self._dropShadowEffect.setOffset(0.0, 10.0)
        self._dropShadowEffect.setBlurRadius(8.0)
        self._dropShadowEffect.setColor(QColor(0, 0, 0, 50))

        self._spacing_constant = 5.0

    def update_layout(self):
        width = self._label.boundingRect().width()
        height = self._label.boundingRect().height()

        width = self._spacing_constant + width + self._spacing_constant
        height = self._spacing_constant + height + self._spacing_constant

        self._label.setPos(self._spacing_constant, self._spacing_constant)

        self.resize(width, height)
        self.update()

    def paint(self, painter, option, widget):
        shape = QPainterPath()
        shape.addRoundedRect(self.rect(), 1, 1)

        #painter.setPen(self._shapePen)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawPath(shape)
        # painter.setPen(self._pen)
        # painter.drawPath(self._path)

    def on_updated(self, center_position, text):
        self._label.setText(text)
        self.update_layout()

        rect = self.rect()

        x_pos = center_position.x()
        y_pos = center_position.y()

        if self.anchor == "center":
            x_pos -= rect.width() / 2
            y_pos -= rect.height() / 2

        self.setPos(x_pos, y_pos)


class NodePreviewView(QGraphicsView):

    def __init__(self, node_manager):
        QGraphicsView.__init__(self)

        self.setScene(NodeUiScene())
        self._preview_update_timer = QTimer(self)
        self._node_manager = node_manager

    def update_preview(self):
        self._preview_update_timer.singleShot(0.01, self._update_preview)

    def _update_preview(self):
        from .node import Node as GUINode
        from ..node import Node, MimicFlags

        for item in self.scene().items():
            if isinstance(item, GUINode):
                item.on_deleted()

        hive_node = Node("<preview>", NodeTypes.HIVE, "<preview>", {}, {})

        for node_name, node in sorted(self._node_manager.nodes.items()):
            # If an input IO bee
            if node.import_path in {"hive.antenna", "hive.entry"}:
                pin = next(iter(node.outputs.values()))
                try:
                    connection = next(iter(pin.connections))

                except StopIteration:
                    continue

                remote_pin = connection.input_pin
                input_pin = hive_node.add_input(node_name, mimic_flags=MimicFlags.SHAPE|MimicFlags.COLOUR)
                input_pin.mimic_other_pin(remote_pin)

            # If an output IO bee
            if node.import_path in {"hive.output", "hive.hook"}:
                pin = next(iter(node.inputs.values()))
                try:
                    connection = next(iter(pin.connections))

                except StopIteration:
                    continue

                remote_pin = connection.output_pin
                output_pin = hive_node.add_output(node_name, mimic_flags=MimicFlags.SHAPE|MimicFlags.COLOUR)
                output_pin.mimic_other_pin(remote_pin)

        gui_node = GUINode(hive_node, self)
        self.scene().addItem(gui_node)
        new_center = self.scene().center = QPointF(self.scene().itemsBoundingRect().center())
        self.centerOn(new_center)

    # Disable events
    def mousePressEvent(self, event):
        return

    def mouseReleaseEvent(self, event):
        return


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

        self._preview_view = NodePreviewView(node_manager)
        self._layout.addWidget(self._preview_view)

        self._node_manager = node_manager
        self._show_source = QPushButton("Show Source")
        self._layout.addWidget(self._show_source)
        self._show_source.clicked.connect(self._show_code)

    def _show_code(self):
        hivemap = self._node_manager.export_hivemap()
        code = hivemap_to_builder_body(hivemap)
        dialogue = SourceCodePreviewDialogue(self, code)
      #  dialogue.setParent(self)
        dialogue.setAttribute(Qt.WA_DeleteOnClose)
        dialogue.show()

    def update_preview(self):
        self._preview_view.update_preview()


class NodeView(IGUINodeManager, QGraphicsView):
    _panning = False

    def __init__(self, folding_window, docstring_window, configuration_window, parameter_window, preview_window):
        QGraphicsView.__init__(self)

        self._zoom = 1.0
        self._zoom_increment = 0.05

        self._panning = False
        self._current_center_point = QPointF()
        self._last_pan_point = QPoint()

        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)

        QShortcut(QKeySequence("Delete"), self, self._on_del_key)
        QShortcut(QKeySequence("Backspace"), self, self._on_backspace_key)
        QShortcut(QKeySequence("Tab"), self, self._on_tab_key)
        QShortcut(QKeySequence("+"), self, self._on_plus_key)
        QShortcut(QKeySequence("-"), self, self._on_minus_key)
        QShortcut(QKeySequence("CTRL+I"), self, self._on_import_hivemap)

        for num in range(1, 10):
            func = functools.partial(self._on_num_key, num)
            QShortcut(QKeySequence(str(num)), self, func)

        self.node_to_qtnode = {}

        self._dropped_node_info = None

        # Node manager
        self.node_manager = NodeManager(gui_node_manager=self)
        self.file_name = None

        # Set windows
        self._folding_window = folding_window
        self._docstring_window = docstring_window
        self._configuration_window = configuration_window
        self._parameter_window = parameter_window
        self._preview_window = preview_window

        self._docstring_widget = QTextEdit()
        self._docstring_widget.textChanged.connect(self._docstring_text_updated)
        self._args_widget = ArgsPanel(self.node_manager)
        self._configuration_widget = ConfigurationPanel(self.node_manager)
        self._folding_widget = FoldingPanel(self.node_manager)
        self._preview_widget = PreviewWidget(self.node_manager)

        # Path editing
        self._cut_start_position = None
        self._slice_path = None

        # Visual slice path
        self._draw_path_item = None

        # Tracked connections
        self._connections = {}
        self._active_connection = None

        self._moved_gui_nodes = set()
        self._position_busy = False

        self.focused_socket = None
        self.type_info_widget = None

    def on_socket_hover(self, socket, event=None):
        widget = self.type_info_widget
        if widget is None:
            # Type info
            self.type_info_widget = widget = FloatingTextWidget(anchor="corner")
            self.scene().addItem(widget)
            widget.setVisible(False)

        if event is not None:
            cursor_pos = QCursor.pos()
            origin = self.mapFromGlobal(cursor_pos)
            scene_pos = self.mapToScene(origin)

            widget.setVisible(True)
            widget.on_updated(scene_pos, repr(socket.parent_socket_row.pin.data_type))

        else:
            widget.setVisible(False)

        self.focused_socket = socket

    @property
    def is_untitled(self):
        return self.file_name is None

    def _docstring_text_updated(self):
        self.node_manager.docstring = self._docstring_widget.toPlainText()

    def on_enter(self):
        self._docstring_window.setWidget(self._docstring_widget)
        self._folding_window.setWidget(self._folding_widget)
        self._configuration_window.setWidget(self._configuration_widget)
        self._parameter_window.setWidget(self._args_widget)
        self._preview_window.setWidget(self._preview_widget)

    def on_exit(self):
        self._docstring_window.setWidget(QWidget())
        self._folding_window.setWidget(QWidget())
        self._configuration_window.setWidget(QWidget())
        self._parameter_window.setWidget(QWidget())
        self._preview_window.setWidget(QWidget())

    def save(self, file_name=None):
        if file_name is None:
            file_name = self.file_name

            if file_name is None:
                raise ValueError("Untitled hivemap cannot be saved without filename")

        node_manager = self.node_manager

        # Export data
        data = node_manager.export()
        with open(file_name, "w") as f:
            f.write(data)

        self.file_name = file_name

    def load(self, file_name=None):
        if file_name is None:
            file_name = self.file_name

            if file_name is None:
                raise ValueError("Untitled hivemap cannot be loaded without filename")

        with open(file_name, 'r') as f:
            data = f.read()

        node_manager = self.node_manager
        try:
            node_manager.load(data)

        except Exception as err:
            print("Error during loading")
            import traceback
            print(traceback.format_exc())
            return

        self._docstring_widget.setPlainText(node_manager.docstring)
        self.file_name = file_name

        self.frame_scene_content()

    def create_node(self, node):
        from .node import Node

        gui_node = Node(node, self)

        self.scene().addItem(gui_node)
        gui_node.update_layout()

        self.node_to_qtnode[node] = gui_node

        # Update preview
        self._preview_widget.update_preview()

    def delete_node(self, node):
        gui_node = self.node_to_qtnode.pop(node)
        gui_node.on_deleted()

        # Update preview
        self._preview_widget.update_preview()

        self.gui_on_selected(None)

    def _socket_from_pin(self, pin):
        gui_node = self.node_to_qtnode[pin.node]
        socket_row = gui_node.get_socket_row(pin.name)
        return socket_row.socket

    def create_connection(self, connection):
        output_pin = connection.output_pin
        input_pin = connection.input_pin

        # Update all socket rows colours for each pin's GUI node
        input_gui_node = self.node_to_qtnode[input_pin.node]
        output_gui_node = self.node_to_qtnode[output_pin.node]

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

        # Use dot style for relationships
        if output_pin.is_proxy or input_pin.is_proxy:
            style = "dot"

        else:
            style = "dashed" if style_pin.mode == "pull" else "solid"

        # TODO work this out properly
        curve = not (output_pin.node.node_type == NodeTypes.HELPER or input_pin.node.node_type == NodeTypes.HELPER)
        gui_connection = Connection(output_socket, input_socket, style=style, curve=curve)

        # Push connections have ordering
        if style_pin.mode == "push":
            gui_connection._center_widget = widget = FloatingTextWidget(gui_connection)
            widget.setVisible(False)

        gui_connection.update_path()

        self._connections[connection] = gui_connection

        # Update preview
        self._preview_widget.update_preview()

    def delete_connection(self, connection):
        gui_connection = self._connections.pop(connection)
        gui_connection.on_deleted()

        # Unset active connection
        if gui_connection is self._active_connection:
            self._active_connection = None

        # Update preview
        self._preview_widget.update_preview()

    def reorder_connection(self, connection, index):
        gui_connection = self._connections[connection]
        output_socket = gui_connection.start_socket
        output_socket.reorder_connection(gui_connection, index)

    def set_node_position(self, node, position):
        gui_node = self.node_to_qtnode[node]

        self._position_busy = True
        gui_node.setPos(*position)
        self._position_busy = False

    def set_node_name(self, node, name):
        gui_node = self.node_to_qtnode[node]
        gui_node.name = name

        # Update preview
        self._preview_widget.update_preview()

    def fold_pin(self, pin):
        self._set_pin_folded(pin, True)

    def unfold_pin(self, pin):
        self._set_pin_folded(pin, False)

    def _set_pin_folded(self, pin, folded):
        # Get node
        node = pin.node
        gui_node = self.node_to_qtnode[node]

        # Get socket
        socket_row = gui_node.get_socket_row(pin.name)

        # Get target
        target_connection = next(iter(pin.connections))
        target_pin = target_connection.output_pin
        target_node = target_pin.node

        target_gui_node = self.node_to_qtnode[target_node]

        target_gui_node.setVisible(not folded)
        socket_row.socket.setVisible(not folded)

    def gui_on_moved(self, gui_node):
        # Don't respond to node_manager set_node_position movements
        if self._position_busy:
            return

        self._moved_gui_nodes.add(gui_node)

    def gui_finished_move(self):
        """Called after all nodes in view have been moved"""
        for gui_node in self._moved_gui_nodes.copy():
            pos = gui_node.pos()
            position = pos.x(), pos.y()

            self.node_manager.set_node_position(gui_node.node, position)

        self._moved_gui_nodes.clear()

    def gui_create_connection(self, start_socket, end_socket):
        start_pin = start_socket.parent_socket_row.pin
        end_pin = end_socket.parent_socket_row.pin

        try:
            self.node_manager.create_connection(start_pin, end_pin)

        except ConnectionError:
            pass

    def gui_delete_connection(self, gui_connection):
        connection = next((k for k, v in self._connections.items() if v is gui_connection))
        self.node_manager.delete_connection(connection)

    def gui_on_selected(self, gui_node):
        if gui_node is None:
            node = None

        else:
            node = gui_node.node

        self._folding_widget.node = node
        self._configuration_widget.node = node
        self._args_widget.node = node

    def gui_set_selected_nodes(self, items):
        self.scene().clearSelection()

        for item in items:
            item.setSelected(True)

    def gui_get_selected_nodes(self):
        from .node import Node

        nodes = []

        selected_items = self.scene().selectedItems()

        for item in selected_items:
            if isinstance(item, Node):
                nodes.append(item)

        return nodes

    def gui_reorder_connection(self, gui_connection, index):
        connection = next((k for k, v in self._connections.items() if v is gui_connection))
        self.node_manager.reorder_connection(connection, index)

    def _on_import_hivemap(self):
        # JUST for testing
        dialogue = DynamicInputDialogue(self)
        dialogue.setAttribute(Qt.WA_DeleteOnClose)
        dialogue.setWindowTitle("Import hivemap")
        dialogue.add_widget("import_path", "str")
        dialogue.exec_()

        hive_path = dialogue.values['import_path']
        from ..utils import class_from_hivemap
        import os

        with open(hive_path, "r") as f:
            data = f.read()

        from ..models.model import Hivemap
        hivemap = Hivemap(data)
        cls = class_from_hivemap(os.path.basename(hive_path), hivemap)

        import dragonfly
        dragonfly._H = cls
        import_path = "dragonfly._H"
        self.node_manager.create_hive(import_path, {})

    def _on_backspace_key(self):
        self._on_del_key()

    def _on_tab_key(self):
        pass

    def _on_plus_key(self):
        active_connection = self._active_connection
        if active_connection is not None:
            start_socket = active_connection.start_socket
            index, _ = start_socket.get_index_info(active_connection)

            self.gui_reorder_connection(active_connection, index + 1)

        focused_socket = self.focused_socket
        if focused_socket is not None:
            focused_socket._on_plus_key()

    def _on_minus_key(self):
        active_connection = self._active_connection
        if active_connection is not None:
            start_socket = active_connection.start_socket
            index, _ = start_socket.get_index_info(active_connection)

            self.gui_reorder_connection(active_connection, index - 1)

        focused_socket = self.focused_socket
        if focused_socket is not None:
            focused_socket._on_minus_key()

    def _on_num_key(self, num):
        pass

    def _on_del_key(self):
        scene = self.scene()

        for gui_node in scene.selectedItems():
            self.node_manager.delete_node(gui_node.node)

    def select_all(self):
        from .node import Node
        nodes = [item for item in self.scene().items() if isinstance(item, Node)]
        self.gui_set_selected_nodes(nodes)

    def undo(self):
        self.node_manager.history.undo()

    def redo(self):
        self.node_manager.history.redo()

    def cut(self):
        gui_nodes = self.gui_get_selected_nodes()
        nodes = [n.node for n in gui_nodes]
        self.node_manager.cut(nodes)

    def copy(self):
        gui_nodes = self.gui_get_selected_nodes()
        nodes = [n.node for n in gui_nodes]
        self.node_manager.copy(nodes)

    def paste(self):
        cursor_pos = QCursor.pos()
        origin = self.mapFromGlobal(cursor_pos)
        scene_pos = self.mapToScene(origin)
        mouse_pos = scene_pos.x(), scene_pos.y()

        self.node_manager.paste(mouse_pos)

    def pre_drop_hive(self, path):
        self._dropped_node_info = NodeTypes.HIVE, path

    def pre_drop_bee(self, path):
        self._dropped_node_info = NodeTypes.BEE, path

    def pre_drop_helper(self, path):
        self._dropped_node_info = NodeTypes.HELPER, path

    def setScene(self, new_scene):
        QGraphicsView.setScene(self, new_scene)

        self.zoom = new_scene.zoom

        new_center = QPointF(new_scene.center_pos)

        self.centerOn(new_center)
        self._current_center_point = new_center

        new_scene.clearSelection()

        if new_scene._first_time_entering:
            self.frame_scene_content()
            new_scene._first_time_entering = False

    def frame_scene_content(self):
        new_center = self.scene().center = QPointF(self.scene().itemsBoundingRect().center())
        self.centerOn(new_center)
        self._current_center_point = new_center

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        event.accept()

        node_info = self._dropped_node_info

        if node_info is None:
            return

        node_type, import_path = node_info
        position = scene_pos.x(), scene_pos.y()

        if node_type == NodeTypes.BEE:
            self.on_dropped_bee(position, import_path)

        elif node_type == NodeTypes.HIVE:
            self.on_dropped_hive(position, import_path)

        elif node_type == NodeTypes.HELPER:
            self.on_dropped_helper(position, import_path)

        else:
            raise ValueError(node_type)

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
            if dialogue_result == QDialog.DialogCode.Rejected:
                raise DynamicInputDialogue.DialogueCancelled("Menu cancelled")

            # Set result
            params[stage_name] = previous_values = dialogue.values

            # Save inspection stage
            inspection_info[stage_name] = stage_options

        return params

    def on_dropped_bee(self, position, import_path):
        inspector = self.node_manager.bee_node_inspector.inspect(import_path)
        params = self._execute_inspector(inspector)

        node = self.node_manager.create_bee(import_path, params=params)
        self.node_manager.set_node_position(node, position)

    def on_dropped_helper(self, position, import_path):
        inspector = self.node_manager.helper_node_inspector.inspect(import_path)
        params = self._execute_inspector(inspector)

        node = self.node_manager.create_helper(import_path, params=params)
        self.node_manager.set_node_position(node, position)

    def on_dropped_hive(self, position, import_path):
        inspector = self.node_manager.hive_node_inspector.inspect(import_path)
        params = self._execute_inspector(inspector)

        node = self.node_manager.create_hive(import_path, params=params)
        self.node_manager.set_node_position(node, position)

    @property
    def center(self):
        return self._current_center_point

    @center.setter
    def center(self, center_point):
        self._current_center_point = center_point
        self.scene().center = center_point
        self.centerOn(self._current_center_point)

    def _find_connection_at(self, position, size):
        point_rect = QRectF(position + QPointF(-size/2, -size/2), QSize(size, size))

        for connection in self._connections.values():
            if not connection.isVisible():
                continue

            if connection.intersects_circle(position, point_rect, size):
                return connection

    def _get_intersected_connections(self, path):
        path_rect = path.boundingRect()
        path_line = QLineF(path.pointAtPercent(0.0), path.pointAtPercent(1.0))

        intersected = []
        for connection in self._connections.values():
            if not connection.isVisible():
                continue

            if connection.intersects_line(path_line, path_rect):
                intersected.append(connection)

        return intersected

    def mousePressEvent(self, mouseEvent):
        if mouseEvent.modifiers() == Qt.ShiftModifier:
            self._last_pan_point = mouseEvent.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self._panning = True

        elif mouseEvent.modifiers() == Qt.ControlModifier:
            self._cut_start_position = self.mapToScene(mouseEvent.pos())

            # Create visible path
            if self._draw_path_item is None:
                self._draw_path_item = self.scene().addPath(QPainterPath())
                color = QColor(255, 0, 0)
                pen = QPen(color)
                self._draw_path_item.setPen(pen)
                self._draw_path_item.setVisible(True)

        else:
            scene_pos = self.mapToScene(mouseEvent.pos())
            connection = self._find_connection_at(scene_pos, SELECT_SIZE)

            # If found connection
            if connection is not None:
                for connection_ in self._connections.values():
                    connection_.set_selected(False)

                # Set selected
                connection.set_selected(True)
                self._active_connection = connection

            # Unselect current
            else:
                connection = self._active_connection
                if connection:
                    connection.set_selected(False)
                    self._active_connection = None

            QGraphicsView.mousePressEvent(self, mouseEvent)
            self.update()

    def mouseMoveEvent(self, mouseEvent):
        if self._panning:
            delta = self.mapToScene(self._last_pan_point) - self.mapToScene(mouseEvent.pos())
            self._last_pan_point = mouseEvent.pos()

            self.center += delta

        # If cutting connections
        elif self._cut_start_position is not None:
            start_scene_pos = self._cut_start_position
            current_scene_pos = self.mapToScene(mouseEvent.pos())

            path = QPainterPath()
            path.moveTo(start_scene_pos)

            path.lineTo(current_scene_pos)
            self._slice_path = path

            # Set new visual path
            self._draw_path_item.setPath(path)

        else:
            QGraphicsView.mouseMoveEvent(self, mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        if self._panning:
            self.setCursor(Qt.ArrowCursor)
            self._last_pan_point = QPoint()
            self._panning = False
            NodeView._panning = False

        # Draw cutting tool
        elif self._slice_path is not None:
            to_remove = self._get_intersected_connections(self._slice_path)

            for connection in to_remove:
                self.gui_delete_connection(connection)

            self._slice_path = None
            self._cut_start_position = None

            # Hide debug path
            self._draw_path_item.setPath(QPainterPath())

        else:
            QGraphicsView.mouseReleaseEvent(self, mouseEvent)

    def wheelEvent(self, event):
        if event.orientation() == Qt.Vertical:
            delta = event.delta()

            if delta > 0:
                self.zoom += 0.05

            else:
                self.zoom -= 0.05

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        self._zoom = zoom

        if zoom >= 1.0:
            self._zoom = 1.0

        elif zoom <= 0.1:
            self._zoom = 0.1

        transform = self.transform()
        new_transform = QTransform.fromTranslate(transform.dx(), transform.dy())
        new_transform.scale(self._zoom, self._zoom)
        self.setTransform(new_transform)

        self.scene().zoom = self._zoom

    def zoom_in(self):
        self.zoom += self._zoom_increment

    def zoom_out(self):
        self.zoom -= self._zoom_increment
