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

import copy
import weakref
from PySide import QtGui, QtCore

from ..sockets import SocketTypes
from ..node_manager import NodeConnectionError


class Socket(QtGui.QGraphicsItem):

    def __init__(self, socket_row, mode, shape, style, parent_item=None, hover_text=None, order_dependent=False):
        if parent_item is None:  # parentItem is used by builtinUis.ContainedAttributeUiProxy
            parent_item = socket_row

        QtGui.QGraphicsItem.__init__(self, parent_item)

        self._parent_node_ui = weakref.ref(socket_row.parent_node_ui)
        self._parent_socket_row = weakref.ref(socket_row)

        assert mode in ("input", "output"), mode
        self._mode = mode

        assert shape in (SocketTypes.circle, SocketTypes.square), shape
        self._shape = shape

        assert style in ("dot", "dashed", "solid"), style
        self._style = style

        self._rect = QtCore.QRectF(0, 0, 12, 12)
        self._color = QtGui.QColor(200, 200, 200)
        self._brush = QtGui.QBrush(self.color())
        self._pen = QtGui.QPen(QtCore.Qt.NoPen)

        self._hover_text = hover_text
        self._is_order_dependent = order_dependent

        self.mixed_color = False

        self.setFlag(QtGui.QGraphicsItem.ItemSendsScenePositionChanges, True)

        self._pen.setWidthF(1.0)

        self.setAcceptsHoverEvents(True)

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
        return self._pen.getStyle() == QtCore.Qt.SolidLine

    @border_enabled.setter
    def border_enabled(self, value):
        if value:
            self._pen.setStyle(QtCore.Qt.SolidLine)

        else:
            self._pen.setStyle(QtCore.Qt.NoPen)

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
        self.scene().focused_socket = self

        for connection in self._connections:
            connection.on_socket_hover_enter()

    def hoverLeaveEvent(self, event):
        self.scene().focused_socket = None

        for connection in self._connections:
            connection.on_socket_hover_exit()

    def setMixedColor(self, value=True):
        self.mixed_color = value

    def update_tooltip(self):
        tooltip = self.parent_socket_row.toolTip()
        if tooltip is None:
            tooltip = ""

        self.setToolTip(tooltip)

    def set_shape(self, shape):
        self._shape = shape

    def set_colour(self, colour):
        self.setColor(QtGui.QColor(*colour))

    def set_style(self, style):
        self._style = style

    def setColor(self, color):
        self._color.setRgb(color.red(), color.green(), color.blue())
        self._brush.setColor(self._color)
        self._pen.setColor(self._color.darker(150))

    def color(self):
        return QtGui.QColor(self._color)

    def setColorRef(self, color):
        self._color = color

    def colorRef(self):
        return self._color

    def mousePressEvent(self, event):
        # QtGui.QGraphicsItem.mousePressEvent(self, event)

        from .connection import Connection

        if self.is_output:
            connection = self._dragging_connection = Connection(self)
            connection.setActive(False)
            connection.show()

    def mouseMoveEvent(self, event):
        if self.is_output:
            connection = self._dragging_connection
            mouse_pos = connection.mapFromScene(event.scenePos())

            end_socket = connection.end_socket
            end_socket.setPos(mouse_pos)

            connection.set_active(False)
            connection.update_end_pos()

        # QtGui.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.is_output:
            connection = self._dragging_connection

            start_socket = connection.start_socket
            target_socket = connection.find_closest_socket()

            connection.on_deleted()
            self._dragging_connection = None

            if target_socket is not None:
                node = self.parent_socket_row.parent_node_ui

                try:
                    node.view.gui_create_connection(start_socket, target_socket)

                except NodeConnectionError:
                    pass

        # QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

    def setVisible(self, flag):
        QtGui.QGraphicsItem.setVisible(self, flag)

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
