from contextlib import redirect_stdout, contextmanager
from code import InteractiveConsole
from io import StringIO
import sys

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

    def __init__(self, prefix='>>>', local_dict=None):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.display_widget = QLabel(self)
        self.display_widget.setFont(QFont("Consolas"))

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.display_widget)

        self.input_widget = QLineEdit(self)
        self.layout.addWidget(self.scroll_area)
        self.layout.addWidget(self.input_widget)

        self.input_widget.returnPressed.connect(self._on_return)

        if local_dict is None:
            local_dict = {}

        self.local_dict = local_dict
        self.console = InteractiveConsole(local_dict)
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

    def _on_return(self):
        command = self.input_widget.text()
        self.input_widget.setText("")

        string_stream = StringIO()

        with redirect_stdout(string_stream), redirect_stderr(string_stream):
            print(self._prefix, command)
            self.console.push(command)

        self._text += string_stream.getvalue()
        self.display_widget.setText(self._text)

