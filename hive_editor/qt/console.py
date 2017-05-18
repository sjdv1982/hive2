import sys
from code import InteractiveConsole
from collections import deque
from contextlib import redirect_stdout, contextmanager
from io import StringIO

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


@contextmanager
def redirect_stderr(stream):
    old_stderr = sys.stderr
    sys.stderr = stream
    try:
        yield
    finally:
        sys.stderr = old_stderr


class ConsoleWidget(QWidget):

    def __init__(self, prefix='>>>', local_dict=None, max_history=15, display_text=""):
        super(ConsoleWidget, self).__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._displayWidget = QLabel(self)
        self._displayWidget.setFont(QFont("Consolas"))

        self._scrollArea = QScrollArea(self)
        self._scrollArea.setWidgetResizable(True)
        self._scrollArea.setWidget(self._displayWidget)
        self._scrollArea.setAlignment(Qt.AlignBottom)

        self._inputWidget = QLineEdit(self)
        self.layout.addWidget(self._scrollArea)
        self.layout.addWidget(self._inputWidget)

        self._inputWidget.returnPressed.connect(self._onReturn)
        self._scrollArea.verticalScrollBar().rangeChanged.connect(self._onRangeChanged)

        if local_dict is None:
            local_dict = {}

        self.local_dict = local_dict

        self._console = InteractiveConsole(local_dict)
        self._history = deque(maxlen=max_history)
        self._maxHistory = max_history
        self._currentCommandIndex = -1

        self._text = display_text
        self._displayWidget.setText(self._text)
        self._prefix = prefix

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self._currentCommandIndex -= 1

        elif event.key() == Qt.Key_Down:
            self._currentCommandIndex += 1

        else:
            return

        self._currentCommandIndex = max(-len(self._history), min(self._currentCommandIndex, -1))

        if not self._history:
            return

        self._inputWidget.setText(self._history[self._currentCommandIndex])

    def _onRangeChanged(self):
        self._scrollArea.verticalScrollBar().setValue(self._scrollArea.verticalScrollBar().maximum())

    def _onReturn(self):
        command = self._inputWidget.text()

        self._history.append(command)
        self._currentCommandIndex = 0
        self._inputWidget.setText("")

        string_stream = StringIO()

        try:
            with redirect_stdout(string_stream), redirect_stderr(string_stream):
                print(self._prefix, command)
                self._console.push(command)

        finally:
            self._text += string_stream.getvalue()
            self._displayWidget.setText(self._text)
            self._displayWidget.update()
            self._scrollArea.update()
