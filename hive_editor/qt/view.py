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

from functools import partial
from operator import attrgetter

from PyQt5.QtWidgets import QGraphicsView, QShortcut
from PyQt5.QtCore import Qt, QTimer, QPoint, QEvent, QPointF, pyqtSignal, QLineF, QRectF, QSizeF
from PyQt5.QtGui import QColor, QPainter, QKeySequence, QPainterPath, QPen, QCursor, QTransform

from .floating_text import FloatingTextWidget
from .scene import NodeUIScene


SELECT_SIZE = 10

get_name = attrgetter("name")


class NodePreviewView(QGraphicsView):

    def __init__(self):
        QGraphicsView.__init__(self)

        self.setScene(NodeUIScene())
        # Timer to update preview - need to introduce small delay to prevent bugs
        self._previewUpdateTimer = QTimer(self)

        # self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def guiOnSocketHover(self, socket, event=None):
        pass

    def guiOnHoverExit(self, node):
        pass

    def guiOnHoverEnter(self, node):
        pass

    def guiOnNodeRightClick(self, node, event):
        pass

    def previewNode(self, node):
        self._previewUpdateTimer.singleShot(0.01, partial(self._updatePreview, node))

    def _updatePreview(self, node):
        from .node import QtNode as GUINode

        for item in self.scene().items():
            if isinstance(item, GUINode):
                item.onDeleted()

        self.scene().clear()

        gui_node = GUINode(node, self)
        self.scene().addItem(gui_node)

        new_center = QPointF(self.scene().itemsBoundingRect().center())
        self.centerOn(new_center)

    # Disable events
    def mousePressEvent(self, event):
        return

    def mouseReleaseEvent(self, event):
        return


class NodeView(QGraphicsView):
    _DEBUGGING_COLOR = QColor(255, 0, 0)
    MOUSE_STEPS = 15

    onConnectionCreated = pyqtSignal(object, object)
    onConnectionReordered = pyqtSignal(object, int)
    onConnectionsDestroyed = pyqtSignal(list)

    onNodesMoved = pyqtSignal(object)
    onNodesDeleted = pyqtSignal(list)

    onNodeSelected = pyqtSignal(object)
    onNodeDeselectd = pyqtSignal(object)
    onNodeRightClick = pyqtSignal(object, QEvent)
    onSocketInteract = pyqtSignal(object)

    onDragMove = pyqtSignal(QEvent)
    onDropped = pyqtSignal(QEvent, QPoint)

    def __init__(self, parent=None):
        QGraphicsView.__init__(self, parent)

        self._zoom = 1.0
        self._zoomIncrement = 0.05

        self._panning = False
        self._currentCenterPoint = QPointF()
        self._lastPanPoint = QPoint()

        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setMouseTracking(True)

        # Path editing
        self._cutStartPosition = None
        self._slicePath = None

        # Visual slice path
        self._drawPathItem = None

        # Tracked connections
        self._connections = set()
        self._activeConnection = None

        self._movedGuiNodes = set()
        self._positionBusy = False

        scene = NodeUIScene(self)
        self.setScene(scene)

        self._focusedSocket = None
        self._hoveredNode = None

        self._typeInfoWidget = FloatingTextWidget(anchor="corner") # TODO
        self._typeInfoWidget.setZValue(1e4)
        self._typeInfoWidget.setVisible(False)
        self.scene().addItem(self._typeInfoWidget)

        # Set rubber band drag

        self.setDragMode(QGraphicsView.RubberBandDrag)

    def onSocketHoverEnter(self, socket, event=None):
        widget = self._typeInfoWidget

        cursor_pos = QCursor.pos()
        origin = self.mapFromGlobal(cursor_pos)
        scene_pos = self.mapToScene(origin)

        widget.setVisible(True)
        widget.onUpdated(scene_pos, socket.parentSocketRow().pin().data_type)

    def onSocketHoverExit(self, socket):
        widget = self._typeInfoWidget
        widget.setVisible(False)
        self._focusedSocket = None

    @property
    def mouse_pos(self):
        cursor_pos = QCursor.pos()
        origin = self.mapFromGlobal(cursor_pos)
        scene_pos = self.mapToScene(origin)
        return scene_pos.x(), scene_pos.y()

    def addNode(self, gui_node):
        self.scene().addItem(gui_node)
        gui_node.updateLayout()

    def removeNode(self, gui_node):
        self.scene().removeItem(gui_node)

    def addConnection(self, gui_connection):
        self._connections.add(gui_connection)
        self.scene().addItem(gui_connection)

    def removeConnection(self, gui_connection):
        # Unset active connection
        if gui_connection is self._activeConnection:
            self._activeConnection = None

        self._connections.remove(gui_connection)
        self.scene().removeItem(gui_connection)

    def reorderConnection(self, gui_connection, index):
        output_socket = gui_connection.startSocket()
        output_socket.reorderConnection(gui_connection, index)

    def setNodePosition(self, gui_node, position):
        self._positionBusy = True
        gui_node.setPos(*position)
        self._positionBusy = False

    def enableSocketDebugging(self, gui_node, socket_row):
        socket_row.setLabelColor(self._DEBUGGING_COLOR)

    def disableSocketDebugging(self, gui_node, socket_row):
        socket_row.setLabelColor(socket_row.defaultColor())

    def blinkConnection(self, gui_connection, time):
        gui_connection.blink(time)

    def setNodeName(self, gui_node, name):
        gui_node.setName(name)

    def foldNode(self, socket_row, target_gui_node):
        self._setNodeFolded(socket_row, target_gui_node, True)

    def unfoldNode(self, socket_row, target_gui_node):
        self._setNodeFolded(socket_row, target_gui_node, False)

    def _setNodeFolded(self, socket_row, target_gui_node, folded):
        target_gui_node.setVisible(not folded)
        socket_row.socket().setVisible(not folded)

    def guiOnMoved(self, gui_node):
        # Don't respond to node_manager set_node_position movements
        if self._positionBusy:
            return

        self._movedGuiNodes.add(gui_node)

    def guiOnSocketInteract(self, socket):
        self.onSocketInteract.emit(socket)

    def guiOnFinishedMove(self):
        """Called after all nodes in view have been moved"""
        self.onNodesMoved.emit(self._movedGuiNodes)

        self._movedGuiNodes.clear()

    def guiCreateConnection(self, start_socket, end_socket):
        self.onConnectionCreated.emit(start_socket, end_socket)

    def guiDeleteConnection(self, gui_connections):
        self.onConnectionsDestroyed.emit(gui_connections)

    def guiReorderConnection(self, gui_connection, index):
        self.onConnectionReordered.emit(gui_connection, index)

    def guiOnNodeSelected(self, gui_node):
        self.onNodeSelected.emit(gui_node)

    def guiOnNodeDeselected(self, gui_node):
        self.onNodeDeselectd.emit(gui_node)

    def guiOnNodeRightClick(self, gui_node, event):
        self.onNodeRightClick.emit(gui_node, event)

    def guiOnHoverEnter(self, node):
        self._hoveredNode = node

    def guiOnHoverExit(self, node):
        if node is self._hoveredNode:
            self._hoveredNode = None

    def guiSetSelectedNodes(self, items):
        self.scene().clearSelection()

        for item in items:
            item.setSelected(True)

    def guiSelectedNodes(self):
        from .node import QtNode

        nodes = []

        selected_items = self.scene().selectedItems()

        for item in selected_items:
            if isinstance(item, QtNode):
                nodes.append(item)

        return nodes

    def _onBackspaceKey(self):
        self._onDelKey()

    def _onKeyUp(self):
        active_connection = self._activeConnection
        if active_connection is not None:
            start_socket = active_connection.startSocket()
            index, _ = start_socket.getIndexInfo(active_connection)

            self.guiReorderConnection(active_connection, index + 1)

        focused_socket = self._focusedSocket
        if focused_socket is not None:
            focused_socket._onKeyUp()

    def _onKeyDown(self):
        active_connection = self._activeConnection
        if active_connection is not None:
            start_socket = active_connection.startSocket()
            index, _ = start_socket.getIndexInfo(active_connection)

            self.guiReorderConnection(active_connection, index - 1)

        focused_socket = self._focusedSocket
        if focused_socket is not None:
            focused_socket._onKeyDown()

    def _onDelKey(self):
        scene = self.scene()

        selected_nodes = scene.selectedItems()
        self.onNodesDeleted.emit(selected_nodes)

    def selectAll(self):
        from .node import QtNode
        nodes = [item for item in self.scene().items() if isinstance(item, QtNode)]
        self.guiSetSelectedNodes(nodes)

    def setScene(self, new_scene):
        super(NodeView, self).setScene(new_scene)

        new_center = QPointF()

        self.centerOn(new_center)
        self._currentCenterPoint = new_center

        new_scene.clearSelection()
        self.frameSceneContent()
        self.setZoom(new_scene.zoom())

    def frameSceneContent(self):
        new_center = QPointF(self.scene().itemsBoundingRect().center())
        self.centerOn(new_center)
        self._currentCenterPoint = new_center

    def dragMoveEvent(self, event):
        self.onDragMove.emit(event)

    def dropEvent(self, event):
        global_pos = self.mapToGlobal(event.pos())
        self.onDropped.emit(event, global_pos)

    @property
    def center(self):
        return self._currentCenterPoint

    @center.setter
    def center(self, center_point):
        self._currentCenterPoint = center_point
        self.centerOn(self._currentCenterPoint)

    def findConnectionAt(self, position, size):
        point_rect = QRectF(position + QPointF(-size/2, -size/2), QSizeF(size, size))

        for connection in self._connections:
            if not connection.isVisible():
                continue

            if connection.intersectsCircle(position, point_rect, size):
                return connection

    def _getIntersectedConnections(self, path):
        path_rect = path.boundingRect()
        path_line = QLineF(path.pointAtPercent(0.0), path.pointAtPercent(1.0))

        intersected = []
        for connection in self._connections:
            if not connection.isVisible():
                continue

            if connection.intersectsLine(path_line, path_rect):
                intersected.append(connection)

        return intersected

    def mousePressEvent(self, event):
        # Handle pan event
        if event.button() == Qt.MiddleButton or \
                (event.button() == Qt.LeftButton and event.modifiers() == Qt.AltModifier):

            if not self._hoveredNode:
                self._lastPanPoint = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                self._panning = True

        # Handle augmented selection
        elif event.button() == Qt.LeftButton:
            # Handle connection deletion
            if event.modifiers() == Qt.ShiftModifier:
                self._cutStartPosition = self.mapToScene(event.pos())

                # Create visible path
                if self._drawPathItem is None:
                    self._drawPathItem = self.scene().addPath(QPainterPath())

                    color = QColor(255, 0, 0)
                    pen = QPen(color)
                    self._drawPathItem.setPen(pen)
                    self._drawPathItem.setVisible(True)

                self.setCursor(Qt.CrossCursor)

            # Select connection
            elif event.modifiers() == Qt.NoModifier:
                scene_pos = self.mapToScene(event.pos())
                connection = self.findConnectionAt(scene_pos, SELECT_SIZE)

                # If found connection
                if connection is not None:
                    for connection_ in self._connections:
                        connection_.setActiveState(False)

                    # Set selected
                    connection.setActiveState(True)
                    self._activeConnection = connection

                # Unselect current
                else:
                    connection = self._activeConnection
                    if connection:
                        connection.setActiveState(False)
                        self._activeConnection = None

                self.update()

        QGraphicsView.mousePressEvent(self, event)

    def mouseMoveEvent(self, mouseEvent):
        if self._panning:
            delta = self.mapToScene(self._lastPanPoint) - self.mapToScene(mouseEvent.pos())
            self._lastPanPoint = mouseEvent.pos()

            self.center += delta

        # If cutting connections
        elif self._cutStartPosition is not None:
            start_scene_pos = self._cutStartPosition
            current_scene_pos = self.mapToScene(mouseEvent.pos())

            path = QPainterPath()
            path.moveTo(start_scene_pos)

            path.lineTo(current_scene_pos)
            self._slicePath = path

            # Set new visual path
            self._drawPathItem.setPath(path)

        else:
            QGraphicsView.mouseMoveEvent(self, mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        if self._panning:
            self.setCursor(Qt.ArrowCursor)
            self._lastPanPoint = QPoint()
            self._panning = False

        # Draw cutting tool
        elif self._slicePath is not None:
            to_remove = self._getIntersectedConnections(self._slicePath)

            self.guiDeleteConnection(to_remove)

            self._slicePath = None
            self._cutStartPosition = None

            # Hide debug path
            self._drawPathItem.setPath(QPainterPath())
            self.setCursor(Qt.ArrowCursor)

        else:
            QGraphicsView.mouseReleaseEvent(self, mouseEvent)

    def wheelEvent(self, event):
        degrees = event.angleDelta() / 8
        steps = degrees / self.MOUSE_STEPS
        self.zoom += self._zoomIncrement * steps.y()

    def keyPressEvent(self, event):
        button = event.key()

        if event.modifiers() in (Qt.NoModifier, Qt.KeypadModifier):
            if button in (Qt.Key_Delete, Qt.Key_Backspace):
                self._onDelKey()
                event.accept()

            elif button == Qt.Key_Up:
                self._onKeyUp()
                event.accept()

            elif button == Qt.Key_Down:
                self._onKeyDown()
                event.accept()

    def zoom(self):
        return self._zoom

    def setZoom(self, zoom):
        self._zoom = zoom

        if zoom >= 1.0:
            self._zoom = 1.0

        elif zoom <= 0.1:
            self._zoom = 0.1

        transform = self.transform()
        new_transform = QTransform.fromTranslate(transform.dx(), transform.dy())
        new_transform.scale(self._zoom, self._zoom)
        self.setTransform(new_transform)

        self.scene().setZoom(self._zoom)

    def zoomIn(self):
        self.setZoom(self._zoom + self._zoomIncrement)

    def zoomOut(self):
        self.setZoom(self._zoom - self._zoomIncrement)
