# <license>
# Copyright (C) 2011 Andrea Interguglielmi, All rights reserved.
# This file is part of the coral repository downloaded from http://code.google.com/p/coral-repo.
#
# Modified for the Hive system by Sjoerd de Vries
# All modifications copyright (C) 2012 Sjoerd de Vries, All rights reserved
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

import collections
import weakref
import functools
import os

from .panels import FoldingPanel, ConfigurationPanel, ArgsPanel
from .utils import create_widget

from ..node_manager import NodeManager
from ..utils import import_from_path, get_builder_class_args
from ..gui_node_manager import IGUINodeManager

import hive
import inspect


class ConfigureNodeDialogue(QDialog):

    def __init__(self, parent, args, non_parameter=False):
        QDialog.__init__(self, parent)

        buttons_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        buttons_box.accepted.connect(self.accept)
        buttons_box.rejected.connect(self.reject)

        self.form_group_box = QGroupBox("Form layout")
        self.value_getters = {}

        layout = QFormLayout()
        self.form_group_box.setLayout(layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.form_group_box)
        main_layout.addWidget(buttons_box)

        self.setLayout(main_layout)

        if non_parameter:
            self.display_raw_args(layout, args)

        else:
            self.display_args(layout, args)

    def display_raw_args(self, layout, args):
        # Draw builder args
        for name, default in args.items():
            widget = QLineEdit()

            if default is not None:
                widget.setText(repr(default))

            def value_getter(widget=widget):
                return eval(widget.text)

            layout.addRow(QLabel(name), widget)
            if name in self.value_getters:
                self.value_getters[name] = value_getter

    def display_args(self, layout, args):
        for name in args:
            param = getattr(args, name)

            options = param.options
            data_type = param.data_type
            default = param.start_value

            widget, controller = create_widget(data_type[0], options)

            if default is not param.NoValue:
                try:
                    controller.value = default

                except Exception as err:
                    print(err)

            layout.addRow(QLabel(name), widget)
            self.value_getters[name] = controller.getter

    def accept(self):
        QDialog.accept(self)

        arg_values = {n: v() for n, v in self.value_getters.items()}
        self.params = arg_values


class NodeView(IGUINodeManager, QGraphicsView):
    _panning = False

    def __init__(self, folding_window, docstring_window, configuration_window, args_window):
        QGraphicsView.__init__(self)

        self._zoom = 1.0
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

        for num in range(1, 10):
            func = functools.partial(self._on_num_key, num)
            QShortcut(QKeySequence(str(num)), self, func)

        self.node_to_qtnode = {}

        self._dropped_hive_path = None

        self.node_manager = NodeManager(gui_node_manager=self)
        self.file_name = None

        # Set windows
        self._folding_window = folding_window
        self._docstring_window = docstring_window
        self._configuration_window = configuration_window
        self._args_window = args_window

        self._folding_widget = FoldingPanel("dragonfly.std.Variable", self.node_manager)
        self._docstring_widget = QTextEdit()
        self._configuration_widget = ConfigurationPanel(self.node_manager)
        self._args_widget = ArgsPanel()

        # Path editing
        self._cut_start_position = None
        self._slice_path = None

        # Visual slice path
        self._draw_path_item = None

        # Tracked connections
        self._connections = []
        self._moved_gui_nodes = set()
        self._position_busy = False

    def on_enter(self):
        self._docstring_window.setWidget(self._docstring_widget)
        self._folding_window.setWidget(self._folding_widget)
        self._configuration_window.setWidget(self._configuration_widget)
        self._args_window.setWidget(self._args_widget)

    def on_exit(self):
        self._docstring_window.setWidget(QWidget())
        self._folding_window.setWidget(QWidget())
        self._configuration_window.setWidget(QWidget())
        self._args_window.setWidget(QWidget())

    @property
    def is_untitled(self):
        return self.file_name is None

    def save(self, file_name=None):
        if file_name is None:
            file_name = self.file_name

            if file_name is None:
                raise ValueError("Untitled hivemap cannot be saved without filename")

        node_manager = self.node_manager

        node_manager.docstring = self._docstring_widget.toPlainText()

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

        node_manager.load(data)

        self._docstring_widget.setPlainText(node_manager.docstring)
        self.file_name = file_name

    def create_node(self, node):
        from .node import Node

        gui_node = Node(node, self)

        self.scene().addItem(gui_node)
        gui_node.update_layout()

        self.node_to_qtnode[node] = gui_node

    def delete_node(self, node):
        gui_node = self.node_to_qtnode.pop(node)
        gui_node.on_deleted()

    def create_connection(self, output, input):
        output_node = output.node
        output_gui_node = self.node_to_qtnode[output_node]

        input_node = input.node
        input_gui_node = self.node_to_qtnode[input_node]

        output_socket_row = output_gui_node.get_socket_row(output.name)
        input_socket_row = input_gui_node.get_socket_row(input.name)

        output_socket = output_socket_row.socket
        input_socket = input_socket_row.socket

        from .connection import Connection
        connection = Connection(output_socket, input_socket)
        connection.update_path()

        self._connections.append(connection)

    def delete_connection(self, output, input):
        output_node = output.node
        output_gui_node = self.node_to_qtnode[output_node]

        input_node = input.node
        input_gui_node = self.node_to_qtnode[input_node]

        output_socket_row = output_gui_node.get_socket_row(output.name)
        input_socket_row = input_gui_node.get_socket_row(input.name)

        output_socket = output_socket_row.socket
        input_socket = input_socket_row.socket

        connection = output_socket.find_connection(input_socket)
        connection.on_deleted()

        self._connections.remove(connection)

    def set_node_position(self, node, position):
        try:
            gui_node = self.node_to_qtnode[node]
        except KeyError:
            print(self.node_to_qtnode, node)
            raise

        self._position_busy = True
        gui_node.setPos(*position)
        self._position_busy = False

    def set_node_name(self, node, name):
        gui_node = self.node_to_qtnode[node]
        gui_node.setName(name)

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
        target_pin = next(iter(pin.targets))
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

        except (ValueError, TypeError):
            pass

    def gui_delete_connection(self, start_socket, end_socket):
        start_pin = start_socket.parent_socket_row.pin
        end_pin = end_socket.parent_socket_row.pin
        self.node_manager.delete_connection(start_pin, end_pin)

    def gui_on_selected(self, gui_node):
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

    def _on_backspace_key(self):
        self._on_del_key()

    def _on_tab_key(self):
        pass

    def _on_plus_key(self):
        self.zoom_in()

        focused_socket = self.scene().focused_socket
        if focused_socket is not None:
            focused_socket._on_plus_key()

    def _on_minus_key(self):
        self.zoom_out()

        focused_socket = self.scene().focused_socket
        if focused_socket is not None:
            focused_socket._on_minus_key()

    def _on_num_key(self, num):
        if num == 6:
            self.node_manager.history.redo()

        elif num == 4:
            self.node_manager.history.undo()

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
        self._dropped_hive_path = path

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
        x, y = scene_pos.x(), scene_pos.y()

        import_path = self._dropped_hive_path

        hive_cls = import_from_path(import_path)
        hive_cls._hive_build_args_wrapper()

        params = {"meta_args": {}, "args": {}, "cls_args": {}}

        meta_args_wrapper = hive_cls._hive_meta_args
        if meta_args_wrapper:
            dialogue = ConfigureNodeDialogue(self, meta_args_wrapper)
            dialogue.setAttribute(Qt.WA_DeleteOnClose)
            dialogue.setWindowTitle("Configure Node: Meta Args")
            dialogue.exec()

            meta_args = params['meta_args'] = dialogue.params

            _, _, hive_object_cls = hive_cls._hive_get_hive_object_cls((), meta_args)

        else:
            hive_object_cls = hive_cls._hive_build(())

        args_wrapper = hive_object_cls._hive_args
        if args_wrapper:
            dialogue = ConfigureNodeDialogue(self, args_wrapper)
            dialogue.setAttribute(Qt.WA_DeleteOnClose)
            dialogue.setWindowTitle("Configure Node: Args")
            dialogue.exec()

            params['args'] = dialogue.params

        builder_args = collections.OrderedDict((k, d['default']) for k, d in get_builder_class_args(hive_cls).items())
        if builder_args:
            dialogue = ConfigureNodeDialogue(self, builder_args, non_parameter=True)
            dialogue.setAttribute(Qt.WA_DeleteOnClose)
            dialogue.setWindowTitle("Configure Node: Class Args")
            dialogue.exec()

            params['cls_args'] = dialogue.params

        node = self.node_manager.create_node(import_path, params=params)
        self.node_manager.set_node_position(node, (x, y))

        event.accept()

    @property
    def center(self):
        return self._current_center_point

    @center.setter
    def center(self, center_point):
        self._current_center_point = center_point
        self.scene().center = center_point
        self.centerOn(self._current_center_point)

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
            QGraphicsView.mousePressEvent(self, mouseEvent)

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
            path = self._slice_path
            path_rect = path.boundingRect()

            to_remove = []
            for connection in self._connections:
                if not connection.isVisible():
                    continue

                scene_translation = connection.start_socket.sceneTransform()
                connection_rect = scene_translation.mapRect(connection._rect)

                if path_rect.intersects(connection_rect):
                    connection_path = scene_translation.map(connection._path)

                    if connection_path.intersects(path):
                        to_remove.append(connection)

            for connection in to_remove:
                self.gui_delete_connection(connection.start_socket, connection.end_socket)

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
        self.zoom += 0.05

    def zoom_out(self):
        self.zoom -= 0.05
