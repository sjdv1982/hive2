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

import functools

from .qt_core import *
from .qt_gui import *
from ..node import NodeTypes

SELECT_SIZE = 10


class NodeView(QGraphicsView):
    _panning = False

    def __init__(self):
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

        for num in range(1, 10):
            func = functools.partial(self._on_num_key, num)
            QShortcut(QKeySequence(str(num)), self, func)

        # Path editing
        self._cut_start_position = None
        self._slice_path = None

        # Visual slice path
        self._draw_path_item = None

        # Tracked connections
        self._connections = set()
        self._active_connection = None

        self._moved_gui_nodes = set()
        self._position_busy = False

        self.focused_socket = None
        self.type_info_widget = None

        self.on_node_moved = None
        self.on_node_deleted = None
        self.on_connection_created = None
        self.on_connection_destroyed = None
        self.on_connection_reordered = None
        self.on_node_selected = None
        self.on_dropped_tree_node = None

    def on_socket_hover(self, socket, event=None):
        widget = self.type_info_widget
        if widget is None:
            # Type info
            self.type_info_widget = widget = FloatingTextWidget(anchor="corner") # TODO
            self.scene().addItem(widget)
            widget.setVisible(False)

        if event is not None:
            cursor_pos = QCursor.pos()
            origin = self.mapFromGlobal(cursor_pos)
            scene_pos = self.mapToScene(origin)

            widget.setVisible(True)
            widget.on_updated(scene_pos, repr(socket.parent_socket_row.pin.data_type)) #TODO

        else:
            widget.setVisible(False)

        self.focused_socket = socket

    @property
    def mouse_pos(self):
        cursor_pos = QCursor.pos()
        origin = self.mapFromGlobal(cursor_pos)
        scene_pos = self.mapToScene(origin)
        return scene_pos.x(), scene_pos.y()

    def add_node(self, gui_node):
        self.scene().addItem(gui_node)
        gui_node.update_layout()

    def remove_node(self, gui_node):
        self.scene().removeItem(gui_node)

    def add_connection(self, gui_connection):
        self._connections.add(gui_connection)

    def remove_connection(self, gui_connection):
        # Unset active connection
        if gui_connection is self._active_connection:
            self._active_connection = None

        self._connections.remove(gui_connection)

    def reorder_connection(self, gui_connection, index):
        output_socket = gui_connection.start_socket
        output_socket.reorder_connection(gui_connection, index)

    def set_node_position(self, gui_node, position):
        self._position_busy = True
        gui_node.setPos(*position)
        self._position_busy = False

    def set_node_name(self, gui_node, name):
        gui_node.name = name

    def fold_pin(self, socket_row, target_gui_node):
        self._set_pin_folded(socket_row, target_gui_node, True)

    def unfold_pin(self, socket_row, target_gui_node):
        self._set_pin_folded(socket_row, target_gui_node, False)

    def _set_pin_folded(self, socket_row, target_gui_node, folded):
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

            if callable(self.on_node_moved):
                self.on_node_moved(gui_node, position)

        self._moved_gui_nodes.clear()

    def gui_create_connection(self, start_socket, end_socket):

        try:
            if callable(self.on_connection_created):
                self.on_connection_created(start_socket, end_socket)

        except ValueError:
            pass

    def gui_delete_connection(self, gui_connection):
        if callable(self.on_connection_destroyed):
            self.on_connection_destroyed(gui_connection)

    def gui_reorder_connection(self, gui_connection, index):
        if callable(self.on_connection_reordered):
            self.on_connection_reordered(gui_connection, index)

    def gui_on_selected(self, gui_node):
        if callable(self.on_node_selected):
            self.on_node_selected(gui_node)

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
            if callable(self.on_node_deleted):
                self.on_node_deleted(gui_node)

    def select_all(self):
        from .node import Node
        nodes = [item for item in self.scene().items() if isinstance(item, Node)]
        self.gui_set_selected_nodes(nodes)

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

        position = scene_pos.x(), scene_pos.y()

        if callable(self.on_dropped_tree_node):
            self.on_dropped_tree_node(position)

    @property
    def center(self):
        return self._current_center_point

    @center.setter
    def center(self, center_point):
        self._current_center_point = center_point
        self.scene().center = center_point
        self.centerOn(self._current_center_point)

    def _find_connection_at(self, position, size):
        point_rect = QRectF(position + QPointF(-size/2, -size/2), QSizeF(size, size))

        for connection in self._connections:
            if not connection.isVisible():
                continue

            if connection.intersects_circle(position, point_rect, size):
                return connection

    def _get_intersected_connections(self, path):
        path_rect = path.boundingRect()
        path_line = QLineF(path.pointAtPercent(0.0), path.pointAtPercent(1.0))

        intersected = []
        for connection in self._connections:
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
                for connection_ in self._connections:
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
