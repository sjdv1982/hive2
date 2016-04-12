from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QPushButton

# TODO expand these
keycodes = {getattr(Qt, n): n for n in dir(Qt) if n.startswith("Key_")}


class QKeySelector(QPushButton):
    keySelected = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._keycode = None
        self._listening = False

        self.clicked.connect(self._listenForEvent)

    def keycode(self):
        return self._keycode

    def setKeycode(self, keycode):
        has_changed = keycode != self._keycode
        self._keycode = keycode
        self.setText(repr(keycode))

        if has_changed:
            self.keySelected.emit(keycode)

    def _listenForEvent(self):
        self._listening = True
        self.setText('Waiting for key...')

    def _stopListening(self):
        self._listening = None

    def keyPressEvent(self, event):
        if not self._listening:
            return super().keyPressEvent(event)

        pressed_key = keycodes[event.key()]
        key_name = pressed_key[len("Key_"):].lower()
        self.setKeycode(key_name)
        self._stopListening()