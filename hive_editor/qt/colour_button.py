from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QPushButton, QColorDialog


class ColorButton(QPushButton):
    colorChanged = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(ColorButton, self).__init__(*args, **kwargs)

        self._colour = QColor()

    def color(self):
        return self._colour

    def setColor(self, colour):
        has_changed = colour != self._colour

        self._colour = colour
        self.setStyleSheet("background-color: {};".format(self._colour.name()))

        if has_changed:
            self.colorChanged.emit()

    def showColorPicker(self):
        dialogue = QColorDialog()
        dialogue.setCurrentColor(self._colour)
        dialogue.setOption(QColorDialog.ShowAlphaChannel)

        if dialogue.exec_():
            self.setColor(dialogue.currentColor())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.showColorPicker()

        return super().mousePressEvent(event)
