
from PySide.QtCore import *
from PySide.QtGui import *

from .view import NodeView

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


import weakref

from .socket import Socket
from ..sockets import get_socket_type_for_mode, get_colour

from collections import OrderedDict


class SocketRow(QGraphicsWidget):

    def __init__(self, parent_node_ui, pin):
        QGraphicsWidget.__init__(self, parent_node_ui)

        self._parent_node_ui = weakref.ref(parent_node_ui)
        self._pin = pin
        self._spacerConstant = 5.0
        self._label = QGraphicsSimpleTextItem(self)

        self._socket = None
        self._outputHook = None

        socket_colour = get_colour(pin.data_type)
        socket_type = get_socket_type_for_mode(pin.mode)

        if pin.io_type == "input":
            self._socket = Socket(self, "input", socket_type, "solid", hover_text="", order_dependent=True)
            self.setHooksColor("input", QColor(*socket_colour))

        else:
            self._socket = Socket(self, "output", socket_type, "solid", hover_text="", order_dependent=True)
            self.setHooksColor("output", QColor(*socket_colour))

        self._socket.setVisible(True)

        self._label.setBrush(parent_node_ui.labelsColor())
        label = self._pin.name
        # if self._params.label is not None:
            # label = self._params.label
        self._labelText = label
        self.setValue("")
        self.setVisible(True)#self._params.visible)

    @property
    def pin(self):
        return self._pin

    @property
    def socket(self):
        return self._socket

    def labelColor(self):
        return self._label.brush().color()

    def setValue(self, value):
        text = self._labelText
        if value is not None:
            if False:#self._params.value_on_newline:
                text += ":\n  "
            else:
                text += ": "
            value2 = value
            pos = value.find("\n")
            if pos > -1:
                value2 = value[:pos] + " ..."
            if len(value2) > 34:
                value2 = value2[:30] + " ..."
            text += value2
        self._label.setText(text)

    def label(self):
        return self._label

    def toolTip(self):
        return ""

    def _disconnected(self):
        if self._socket.mode == "input":
            # TODO
            pass
            if self._socket._connections:
                self._socket._connections[0].on_deleted()

    def setHooksColor(self, io, color, mixedColor=False):
        self._socket.setColor(color)
        self._socket.setMixedColor(mixedColor)

    @property
    def parent_node_ui(self):
        parent = None

        if self._parent_node_ui:
            parent = self._parent_node_ui()

        return parent

    @parent_node_ui.setter
    def parent_node_ui(self, node_ui):
        self.setParentItem(None)

        if self.scene():
            if self in self.scene().items():
                self.scene().removeItem(self)

        # Current parent
        if self._parent_node_ui:
            parent_node_ui = self._parent_node_ui()

            if self in parent_node_ui._socket_rows:
                parent_node_ui._socket_rows.remove(self)

        if node_ui:
            self._parent_node_ui = weakref.ref(node_ui)

            self.setParentItem(node_ui)

            if self not in node_ui._socket_rows:
                node_ui._socket_rows.append(self)

        else:
            self._parent_node_ui = None

    def update_layout(self):
        height = self._label.boundingRect().height()
        hook = self._socket

        if hook.mode == "output":
            hook_y_pos = (height - hook.boundingRect().height()) / 2.0

        else:
            hook_y_pos = (height - hook.boundingRect().height()) / 2.0
            hook.setPos(0.0, hook_y_pos)

        input_width = self._spacerConstant * 2.0
        self._label.setPos(input_width + self._spacerConstant, 0)

        if hook.mode == "output":
            hook.setPos(self._label.pos().x() + self._label.boundingRect().width() + self._spacerConstant,
                        hook_y_pos)

            self.resize(hook.pos().x() + hook.boundingRect().width(), height)

        else:
            self.resize(self._label.pos().x() + self._label.boundingRect().width(), height)

    def on_deleted(self):
        if self._socket:
            self._socket.on_deleted()

        self.parent_node_ui = None


class Node(QGraphicsWidget):

    def __init__(self, node, view):
        QGraphicsWidget.__init__(self)

        self._spacerConstant = 5.0
        self._label = QGraphicsSimpleTextItem(self)
        self._shapePen = QPen(Qt.NoPen)
        self._socket_rows = OrderedDict()
        self._brush = QBrush(self.color())
        self._selectedColor = QColor(255, 255, 255)
        self._dropShadowEffect = QGraphicsDropShadowEffect()
        self._showingRightClickMenu = False
        self._rightClickMenuItems = []
        self._doubleClicked = False
        self._zValue = self.zValue()
        self._currentMagnifyFactor = 1.0
        self._deleted = False

        self.setGraphicsEffect(self._dropShadowEffect)

        self._dropShadowEffect.setOffset(0.0, 10.0)
        self._dropShadowEffect.setBlurRadius(8.0)
        self._dropShadowEffect.setColor(QColor(0, 0, 0, 50))

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        self._label.setBrush(self.labelsColor())

        self._shapePen.setColor(self._selectedColor)
        self._shapePen.setWidthF(1.5)

        self._label.setText(node.name)

        self.setToolTip(node.docstring)

        self._node = node
        self._view = weakref.ref(view)

        self._name = node.name

        self._build(node)

    @property
    def node(self):
        return self._node

    @property
    def view(self):
        return self._view()

    def _magnifyAnimStep(self, frame):
        pass

    def _magnify(self, factor):
        pass

    def on_deleted(self):
        self._deleted = True

        if self.isSelected():
            self.setSelected(False)

        for socket_row in self._socket_rows.values():
            socket_row.on_deleted()

        self._socket_rows.clear()

        if self.scene():
            if self in self.scene().items():
                self.scene().removeItem(self)

    def hoverEnterEvent(self, event):
        pass

    def hoverLeaveEvent(self, event):
        pass

    def setName(self, name):
        self._label.setText(name)
        self.update_layout()

    def addRightClickMenuItem(self, label, callback):
        pass

    def showRightClickMenu(self):
        pass

    def shapePen(self):
        return QPen(self._shapePen)

    def color(self):
        return QColor(0, 0, 0)

    def labelsColor(self):
        return QColor(255, 255, 255)

    def onSelected(self):
        if self._deleted:
            return

        if self.isSelected():
            self._shapePen.setStyle(Qt.SolidLine)

        else:
            self._shapePen.setStyle(Qt.NoPen)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.onSelected()

        return value

    def paint(self, painter, option, widget):
        shape = QPainterPath()
        shape.addRoundedRect(self.rect(), 2, 2)

        painter.setPen(self._shapePen)
        painter.setBrush(self._brush)
        painter.drawPath(shape)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            pass

        else:
            QGraphicsWidget.mousePressEvent(self, event)

    def setPos(self, *pos):
        if len(pos) == 1:
            point = QPointF(pos[0])

        else:
            point = QPointF(*pos)

        self._lastPos = point

        QGraphicsWidget.setPos(self, point)

        # On moved
        for socket_row in self._socket_rows.values():
            socket_row.socket.update_connection_positions()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag_position = self.pos()
            position = drag_position.x(), drag_position.y()
            self.view.gui_on_moved(self, position)

        QGraphicsWidget.mouseReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        # On moved
        for socket_row in self._socket_rows.values():
            socket_row.socket.update_connection_positions()

        QGraphicsWidget.mouseMoveEvent(self, event)

    def dragMoveEvent(self, *args, **kwargs):
        pass

    def mouseDoubleClickEvent(self, event):
        pass

    def get_socket_row(self, name):
        return self._socket_rows[name]

    def _build(self, node):
        for pin_name in node.pin_order:
            if pin_name in node.inputs:
                pin = node.inputs[pin_name]

            else:
                pin = node.outputs[pin_name]

            socket_row = SocketRow(self, pin)
            self._socket_rows[pin_name] = socket_row

    def update_layout(self):
        label_width = self._label.boundingRect().width()
        width = label_width
        y_pos = self._label.boundingRect().bottom() + self._spacerConstant

        for socket_row in self._socket_rows.values():
            if socket_row.isVisible():
                socket_row.update_layout()

                socket_row.setPos(self._spacerConstant, y_pos)
                height = socket_row.boundingRect().height()

                y_pos += height

                attributeWidth = socket_row.boundingRect().width()
                if attributeWidth > width:
                    width = attributeWidth

        for socket_row in self._socket_rows.values():
            if socket_row.isVisible():
                hook = socket_row.socket
                if hook.is_output:
                    hook.setPos(width - hook.boundingRect().width(), hook.pos().y())

        width = self._spacerConstant + width + self._spacerConstant
        self._label.setPos((width - label_width) / 2.0, self._spacerConstant)

        self.resize(width, y_pos + self._spacerConstant)
        self.update()