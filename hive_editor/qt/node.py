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


from collections import OrderedDict
import weakref

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtWidgets import QGraphicsWidget, QGraphicsSimpleTextItem, QGraphicsItem, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor, QBrush, QPen, QPainterPath

from .socket import QtSocket
from ..node import NodeTypes


COLOUR_THEMES = {NodeTypes.HIVE: (0, 0, 0), NodeTypes.BEE: (92, 92, 92), NodeTypes.HELPER: (0, 0, 0, 60)}


class SocketRow(QGraphicsWidget):

    def __init__(self, qt_node, pin):
        super(SocketRow, self).__init__()

        assert qt_node is not None
        self.setParentItem(qt_node)
        self._parent_node = weakref.ref(qt_node)
        self._pin = pin
        self._spacerConstant = 5.0
        self._label = QGraphicsSimpleTextItem(self)

        self._socket = None
        self._outputHook = None

        socket_colour = QColor(*pin.colour)
        socket_type = pin.shape

        if pin.io_type == "input":
            self._socket = QtSocket(self, "input", socket_type)
            self._socket.setColor(socket_colour)

        else:
            self._socket = QtSocket(self, "output", socket_type)
            self._socket.setColor(socket_colour)

        self.setLabelColor(self.defaultColor())
        self.setLabelText(self._pin.name)

        self._socket.setVisible(True)

    def parentNode(self):
        return self._parent_node()

    def pin(self):
        return self._pin

    def socket(self):
        return self._socket

    def defaultColor(self):
        return self._parent_node().labelColor()

    def labelColor(self):
        return self._label.brush().color()

    def setLabelColor(self, color):
        self._label.setBrush(color)

    def labelText(self):
        return self._label.text()

    def setLabelText(self, text):
        self._label.setText(text)

    def refresh(self):
        # Update cosmetics
        colour = QColor(*self._pin.colour)
        self._socket.setColor(colour)
        self._socket.setShape(self._pin.shape)
        self._socket.update()

    def updateLayout(self):
        height = self._label.boundingRect().height()
        hook = self._socket

        if hook.mode() == "output":
            hook_y_pos = (height - hook.boundingRect().height()) / 2.0

        else:
            hook_y_pos = (height - hook.boundingRect().height()) / 2.0
            hook.setPos(0.0, hook_y_pos)

        input_width = self._spacerConstant * 2.0
        self._label.setPos(input_width + self._spacerConstant, 0)

        if hook.mode() == "output":
            hook.setPos(self._label.pos().x() + self._label.boundingRect().width() + self._spacerConstant,
                        hook_y_pos)

            self.resize(hook.pos().x() + hook.boundingRect().width(), height)

        else:
            self.resize(self._label.pos().x() + self._label.boundingRect().width(), height)

    def onDeleted(self):
        if self._socket:
            self._socket.onDeleted()

        #self.parent_node_ui = None # TODO


class QtNode(QGraphicsWidget):

    def __init__(self, node, view):
        super(QtNode, self).__init__()

        self._spacingConstant = 5.0
        self._roundness = 3

        self._labelColor = QColor(255, 255, 255)
        self._label = QGraphicsSimpleTextItem(self)
        self._label.setBrush(self._labelColor)
        self._label.setText(node.name)

        self._selectedColor = QColor(255, 255, 255)
        self._shapePen = QPen(Qt.NoPen)
        self._shapePen.setColor(self._selectedColor)
        self._shapePen.setWidthF(1.5)

        self._brush = QBrush(QColor(*COLOUR_THEMES[node.node_type]))

        self._dropShadowEffect = QGraphicsDropShadowEffect()
        self.setGraphicsEffect(self._dropShadowEffect)

        self._dropShadowEffect.setOffset(0.0, 10.0)
        self._dropShadowEffect.setBlurRadius(8.0)
        self._dropShadowEffect.setColor(QColor(0, 0, 0, 50))

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        self.setToolTip(node.tooltip)

        self._name = node.name
        self._node = node
        self._view = weakref.ref(view)

        self._busy = False
        self._socketRows = OrderedDict()

        # Build IO pin socket rows
        for pin_name in node.pin_order:
            if pin_name in node.inputs:
                pin = node.inputs[pin_name]

            else:
                pin = node.outputs[pin_name]

            socket_row = SocketRow(self, pin)
            self._socketRows[pin_name] = socket_row

        self.updateLayout()

    def node(self):
        return self._node

    def view(self):
        return self._view()

    def name(self):
        return self._name

    def setName(self, name):
        self._name = name
        self._label.setText(name)
        self.updateLayout()

    def labelColor(self):
        return self._labelColor

    def onDeleted(self):
        if self.isSelected():
            self.setSelected(False)

        for socket_row in self._socketRows.values():
            socket_row.onDeleted()

        self._socketRows.clear()

    def hoverEnterEvent(self, event):
        self.view().guiOnHoverEnter(self)

    def hoverLeaveEvent(self, event):
        self.view().guiOnHoverExit(self)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for socket_row in self._socketRows.values():
                socket_row.socket().updateConnectionPositions()

            # Move node
            if not self._busy:
                self._busy = True

                self.view().guiOnMoved(self)
                self._busy = False

        elif change == QGraphicsItem.ItemSelectedHasChanged:
            self.onSelected()

        return QGraphicsItem.itemChange(self, change, value)

    def contextMenuEvent(self, event):
        self.view().guiOnNodeRightClick(self, event)

    def onSelected(self):
        if self.isSelected():
            self._shapePen.setStyle(Qt.SolidLine)
            self.view().guiOnNodeSelected(self)

        else:
            self._shapePen.setStyle(Qt.NoPen)
            self.view().guiOnNodeDeselected(self)

    def paint(self, painter, option, widget):
        shape = QPainterPath()
        shape.addRoundedRect(self.rect(), self._roundness, self._roundness)

        painter.setPen(self._shapePen)
        painter.setBrush(self._brush)
        painter.drawPath(shape)

    def setPos(self, *pos):
        if len(pos) == 1:
            point = QPointF(pos[0])

        else:
            point = QPointF(*pos)

        self._lastPos = point

        QGraphicsWidget.setPos(self, point)

    def mouseDoubleClickEvent(self, event):
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            pass

        else:
            QGraphicsWidget.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.view().guiOnFinishedMove()

        QGraphicsWidget.mouseReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        QGraphicsWidget.mouseMoveEvent(self, event)

    def dragMoveEvent(self, *args, **kwargs):
        pass

    def getSocketRow(self, name):
        return self._socketRows[name]

    def refreshSocketRows(self):
        for socket_row in self._socketRows.values():
            socket_row.refresh()

    def updateLayout(self):
        label_width = self._label.boundingRect().width()
        width = label_width
        y_pos = self._label.boundingRect().bottom() + self._spacingConstant

        for socket_row in self._socketRows.values():
            if socket_row.isVisible():
                socket_row.updateLayout()

                socket_row.setPos(self._spacingConstant, y_pos)
                height = socket_row.boundingRect().height()

                y_pos += height

                attributeWidth = socket_row.boundingRect().width()
                if attributeWidth > width:
                    width = attributeWidth

        for socket_row in self._socketRows.values():
            if socket_row.isVisible():
                hook = socket_row.socket()
                if hook.isOutput():
                    hook.setPos(width - hook.boundingRect().width(), hook.pos().y())

        width = self._spacingConstant + width + self._spacingConstant
        self._label.setPos((width - label_width) / 2.0, self._spacingConstant)

        self.resize(width, y_pos + self._spacingConstant)
        self.update()
