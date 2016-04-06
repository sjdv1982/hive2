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

import weakref

from PyQt5.QtWidgets import QGraphicsItem
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtCore import QRectF, Qt

from ..node_manager import NodeConnectionError
from ..sockets import SocketTypes


class Socket(QGraphicsItem):

    def __init__(self, socket_row, mode, shape, parent_item=None, hover_text="", order_dependent=False):
        if parent_item is None:  # parentItem is used by builtinUis.ContainedAttributeUiProxy
            parent_item = socket_row

        QGraphicsItem.__init__(self, parent_item)

        self._parent_node_ui = weakref.ref(socket_row.parent_node_ui)
        self._parent_socket_row = weakref.ref(socket_row)

        assert mode in ("input", "output"), mode
        self._mode = mode

        assert shape in (SocketTypes.circle, SocketTypes.square), shape
        self._shape = shape

        self._rect = QRectF(0, 0, 12, 12)
        self._color = QColor(200, 200, 200)
        self._brush = QBrush(self.color())
        self._pen = QPen(Qt.NoPen)

        self._hover_text = hover_text
        self._is_order_dependent = order_dependent

        self.mixed_color = False

        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)

        self._pen.setWidthF(1.0)

        self.setAcceptHoverEvents(True)
        self.setToolTip(hover_text)

        self._dragging_connection = None
        self._connections = []

    @property
    def mode(self):
        return self._mode

    @property
    def is_input(self):
        return self._mode == "input"

    @property
    def is_output(self):
        return self._mode == "output"

    @property
    def parent_node_ui(self):
        return self._parent_node_ui()

    @property
    def parent_socket_row(self):
        return self._parent_socket_row()

    @property
    def border_enabled(self):
        return self._pen.getStyle() == Qt.SolidLine

    @border_enabled.setter
    def border_enabled(self, value):
        if value:
            self._pen.setStyle(Qt.SolidLine)

        else:
            self._pen.setStyle(Qt.NoPen)

    def add_connection(self, connection):
        self._connections.append(connection)

    def remove_connection(self, connection):
        self._connections.remove(connection)

    def find_connection(self, socket):
        for connection in self._connections:
            if connection.end_socket is socket:
                return connection

            if connection.start_socket is socket:
                return connection

    def reorder_connection(self, connection, index):
        current_index = self._connections.index(connection)
        del self._connections[current_index]
        self._connections.insert(index, connection)

        # Update all paths
        for _connection in self._connections:
            _connection.update_path()
            print("UPDATE PATHS")

    def get_index_info(self, connection):
        index = self._connections.index(connection)
        return index, len(self._connections)

    def _tabKey(self):
        pass

    def _bspKey(self):
        pass

    def _deleteKey(self):
        pass

    def _on_plus_key(self):
        pass

    def _on_minus_key(self):
        pass

    def _numKey(self, num):
        pass

    def hoverEnterEvent(self, event):
        self.parent_node_ui.view.on_socket_hover_enter(self, event)

        for connection in self._connections:
            connection.on_socket_hover_enter()

    def hoverLeaveEvent(self, event):
        for connection in self._connections:
            connection.on_socket_hover_exit()

        self.parent_node_ui.view.on_socket_hover_exit(self)

    def setMixedColor(self, value=True):
        self.mixed_color = value

    def set_shape(self, shape):
        self._shape = shape

    def set_colour(self, colour):
        self.setColor(QColor(*colour))

    def setColor(self, color):
        self._color.setRgb(color.red(), color.green(), color.blue())
        self._brush.setColor(self._color)
        self._pen.setColor(self._color.darker(150))

    def color(self):
        return QColor(self._color)

    def setColorRef(self, color):
        self._color = color

    def colorRef(self):
        return self._color

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.NoModifier:
            from .connection import Connection

            if self.is_output:
                connection = self._dragging_connection = Connection(self)
                self.scene().addItem(connection)
                connection.setActive(False)
                connection.show()

        elif event.button() == Qt.MiddleButton or \
                (event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier):

            self.parent_node_ui.view.gui_on_socket_interact(self)

    def mouseMoveEvent(self, event):
        connection = self._dragging_connection

        if self.is_output and connection is not None:
            mouse_pos = connection.mapFromScene(event.scenePos())

            end_socket = connection.end_socket
            end_socket.setPos(mouse_pos)

            connection.set_active(False)
            connection.update_end_pos()

        # QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.NoModifier:
            if self.is_output:
                connection = self._dragging_connection

                start_socket = connection.start_socket
                target_socket = connection.find_closest_socket()

                connection.on_deleted()
                self.scene().removeItem(connection)

                self._dragging_connection = None

                if target_socket is not None:
                    node = self.parent_node_ui

                    try:
                        node.view.gui_create_connection(start_socket, target_socket)

                    except NodeConnectionError:
                        pass

        # QGraphicsItem.mouseReleaseEvent(self, event)

    def setVisible(self, flag):
        QGraphicsItem.setVisible(self, flag)

        for connection in self._connections:
            connection.update_visibility()

    def update_connection_positions(self):
        """Update connection positions when nodes are moved"""
        for connection in self._connections:
            if connection.start_socket is self:
                connection.update_start_pos()

            else:
                connection.update_end_pos()

    def boundingRect(self):
        return self._rect

    def paint(self, painter, option, widget):

        painter.setBrush(self._brush)
        painter.setPen(self._pen)

        if self._shape == SocketTypes.circle:
            painter.drawEllipse(self._rect)

        elif self._shape == SocketTypes.square:
            painter.save()
            c = self._rect.center()
            painter.translate(c)
            painter.rotate(45)
            painter.scale(0.8, 0.8)
            painter.drawRect(self._rect.translated(-c))
            painter.restore()

        else:
            raise ValueError(self._shape)

        if self.mixed_color:
            painter.setBrush(painter.brush().color().darker(130))
            painter.drawChord(self._rect, 1 * 16, 180 * 16)

    def on_deleted(self):
        pass

    def contextMenuEvent(self, event):
        self.parent_node_ui.view.gui_on_socket_right_click(self, event)