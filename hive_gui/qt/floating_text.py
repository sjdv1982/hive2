from .qt_gui import *


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
