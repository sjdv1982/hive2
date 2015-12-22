from collections import deque
from contextlib import redirect_stdout, contextmanager
from code import InteractiveConsole
from io import StringIO
import sys

from .qt_core import *

from .qt_gui import *


@contextmanager
def redirect_stderr(stream):
    old_stderr = sys.stderr
    sys.stderr = stream
    try:
        yield
    finally:
        sys.stderr = old_stderr


class QConsole(QWidget):

    def __init__(self, prefix='>>>', local_dict=None, max_history=15):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.display_widget = QLabel(self)
        self.display_widget.setFont(QFont("Consolas"))

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.display_widget)
        self.scroll_area.setAlignment(Qt.AlignBottom)

        self.input_widget = QLineEdit(self)
        self.layout.addWidget(self.scroll_area)
        self.layout.addWidget(self.input_widget)

        self.input_widget.returnPressed.connect(self._on_return)
        self.scroll_area.verticalScrollBar().rangeChanged.connect(self._on_range_changed)

        if local_dict is None:
            local_dict = {}

        self.local_dict = local_dict
        self.console = InteractiveConsole(local_dict)
        self._history = deque(maxlen=max_history)
        self._max_history = max_history
        self._current_command = -1
        self._text = """
Hive GUI console.

Available modules:
--------------------
editor - current node editor
window - main window
--------------------
"""
        self.display_widget.setText(self._text)
        self._prefix = prefix

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self._current_command -= 1

        elif event.key() == Qt.Key_Down:
            self._current_command += 1

        else:
            return

        self._current_command = max(-len(self._history), min(self._current_command, -1))

        if not self._history:
            return

        self.input_widget.setText(self._history[self._current_command])

    def _on_range_changed(self):
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def _on_return(self):
        command = self.input_widget.text()

        self._history.append(command)
        self._current_command = 0
        self.input_widget.setText("")

        string_stream = StringIO()

        try:
            with redirect_stdout(string_stream), redirect_stderr(string_stream):
                print(self._prefix, command)
                self.console.push(command)

        finally:
            self._text += string_stream.getvalue()
            self.display_widget.setText(self._text)
            self.display_widget.update()
            self.scroll_area.update()

