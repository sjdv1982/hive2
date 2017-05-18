from PyQt5.QtWidgets import QGraphicsWidget, QGraphicsSimpleTextItem, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor, QPainterPath, QBrush


class FloatingTextWidget(QGraphicsWidget):

    def __init__(self, parent=None, anchor="center"):
        QGraphicsWidget.__init__(self, parent)

        assert anchor in {"center", "corner"}
        self.anchor = anchor

        self._label = QGraphicsSimpleTextItem(self)
        self._label.setBrush(QColor(255, 255, 255))

        # Add drop shadow
        self._dropShadowEffect = QGraphicsDropShadowEffect()
        self.setGraphicsEffect(self._dropShadowEffect)

        self._dropShadowEffect.setOffset(0.0, 10.0)
        self._dropShadowEffect.setBlurRadius(8.0)
        self._dropShadowEffect.setColor(QColor(0, 0, 0, 50))

        self._spacingConstant = 5.0

    def updateLayout(self):
        width = self._label.boundingRect().width()
        height = self._label.boundingRect().height()

        width = self._spacingConstant + width + self._spacingConstant
        height = self._spacingConstant + height + self._spacingConstant

        self._label.setPos(self._spacingConstant, self._spacingConstant)

        self.resize(width, height)
        self.update()

    def paint(self, painter, option, widget):
        shape = QPainterPath()
        shape.addRoundedRect(self.rect(), 1, 1)

        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawPath(shape)

        # painter.setPen(self._pen)
        # painter.drawPath(self._path)

    def onUpdated(self, center_position, text):
        self._label.setText(text)
        self.updateLayout()

        rect = self.rect()

        x_pos = center_position.x()
        y_pos = center_position.y()

        if self.anchor == "center":
            x_pos -= rect.width() / 2
            y_pos -= rect.height() / 2

        else:
            y_pos -= rect.height()

        self.setPos(x_pos, y_pos)
