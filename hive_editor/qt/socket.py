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


class QtSocket(QGraphicsItem):

    def __init__(self, socket_row, mode, shape, hover_text="", order_dependent=False, parent_item=None):
        # If creating a temporary connection, we create a fake socket, whose parent != socket row
        if parent_item is None:
            parent_item = socket_row

        super(QtSocket, self).__init__(parent_item)
        self._parentSocketRow = weakref.ref(socket_row)

        assert mode in ("input", "output"), mode
        self._mode = mode

        assert shape in (SocketTypes.circle, SocketTypes.square), shape
        self._shape = shape

        self._rect = QRectF(0, 0, 12, 12)
        self._color = QColor(200, 200, 200)
        self._brush = QBrush(self.color())
        self._pen = QPen(Qt.NoPen)

        self._hoverText = hover_text
        self._isOrderDependent = order_dependent

        self._mixedColor = False

        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)

        self._pen.setWidthF(1.0)

        self.setAcceptHoverEvents(True)
        self.setToolTip(hover_text)

        self._draggingConnection = None
        self._connections = []

    def mode(self):
        return self._mode

    def isInput(self):
        return self._mode == "input"

    def isOutput(self):
        return self._mode == "output"

    def parentNode(self):
        return self._parentSocketRow().parentNode()

    def parentSocketRow(self):
        return self._parentSocketRow()

    def borderEnabled(self):
        return self._pen.getStyle() == Qt.SolidLine

    def setBorderEnabled(self, value):
        if value:
            self._pen.setStyle(Qt.SolidLine)

        else:
            self._pen.setStyle(Qt.NoPen)

    def addConnection(self, connection):
        self._connections.append(connection)

    def removeConnection(self, connection):
        self._connections.remove(connection)

    def findConnection(self, socket):
        for connection in self._connections:
            if connection.endSocket() is socket:
                return connection

            if connection.startSocket() is socket:
                return connection

    def reorderConnection(self, connection, index):
        current_index = self._connections.index(connection)
        del self._connections[current_index]
        self._connections.insert(index, connection)

        # Update all paths
        for _connection in self._connections:
            _connection.updatePath()
            print("UPDATE PATHS")

    def getIndexInfo(self, connection):
        index = self._connections.index(connection)
        return index, len(self._connections)

    def hoverEnterEvent(self, event):
        self.parentNode().view().onSocketHoverEnter(self, event)

        for connection in self._connections:
            connection.onSocketHoverEnter()

    def hoverLeaveEvent(self, event):
        for connection in self._connections:
            connection.onSocketHoverExit()

        self.parentNode().view().onSocketHoverExit(self)

    def setMixedColor(self, value=True):
        self._mixedColor = value

    def setShape(self, shape):
        self._shape = shape

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

            if self.isOutput():
                connection = self._draggingConnection = Connection(self)
                self.scene().addItem(connection)
                connection.setActive(False)
                connection.show()

        elif event.button() == Qt.MiddleButton or \
                (event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier):

            self.parentNode().view().guiOnSocketInteract(self)

    def mouseMoveEvent(self, event):
        connection = self._draggingConnection

        if self.isOutput() and connection is not None:
            mouse_pos = connection.mapFromScene(event.scenePos())

            end_socket = connection.endSocket()
            end_socket.setPos(mouse_pos)

            connection.setActiveState(False)
            connection.updateEndPos()

        # QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.NoModifier:
            if self.isOutput():
                connection = self._draggingConnection

                start_socket = connection.startSocket()
                target_socket = connection.findClosestSocket()

                connection.onDeleted()
                self.scene().removeItem(connection)

                self._draggingConnection = None

                if target_socket is not None:
                    node = self.parentNode()

                    try:
                        node.view().guiCreateConnection(start_socket, target_socket)

                    except NodeConnectionError:
                        pass

        # QGraphicsItem.mouseReleaseEvent(self, event)

    def setVisible(self, flag):
        QGraphicsItem.setVisible(self, flag)

        for connection in self._connections:
            connection.updateVisibility()

    def updateConnectionPositions(self):
        """Update connection positions when nodes are moved"""
        for connection in self._connections:
            if connection.startSocket() is self:
                connection.updateStartPos()

            else:
                connection.updateEndPos()

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

        if self._mixedColor:
            painter.setBrush(painter.brush().color().darker(130))
            painter.drawChord(self._rect, 1 * 16, 180 * 16)

    def onDeleted(self):
        pass
