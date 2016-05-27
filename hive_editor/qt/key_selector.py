from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QPushButton

import string


keymap = {}

# Map ascii letters
for c in string.ascii_lowercase:
    keycode = getattr(Qt, "Key_{}".format(c.upper()))
    keymap[keycode] = c


# Map digits
for c in string.digits:
    keycode = getattr(Qt, "Key_{}".format(c))
    keymap[keycode] = c


# Map function keys
for i in range(1, 36):
    keycode = getattr(Qt, "Key_F{}".format(i))
    keymap[keycode] = 'f{}'.format(i)

keymap[Qt.Key_Alt] = 'alt'
keymap[Qt.Key_Control] = 'control'
keymap[Qt.Key_Delete] = 'delete'
keymap[Qt.Key_End] = 'end'
keymap[Qt.Key_Home] = 'home'

keymap[Qt.Key_PageDown] = 'page_down'
keymap[Qt.Key_PageUp] = 'page_up'

keymap[Qt.Key_Insert] = 'insert'
keymap[Qt.Key_Backspace] = 'backspace'

keymap[Qt.Key_Exclam] = '!'
keymap[Qt.Key_Semicolon] = ';'
keymap[Qt.Key_Comma] = ','
keymap[Qt.Key_Apostrophe] = "'"
keymap[Qt.Key_Period] = '.'
keymap[Qt.Key_Slash] = "/"
keymap[Qt.Key_Backslash] = "\\"
keymap[Qt.Key_BracketLeft] = "["
keymap[Qt.Key_BracketRight] = "]"
keymap[Qt.Key_Minus] = "-"
keymap[Qt.Key_Plus] = "+"
keymap[Qt.Key_Equal] = "="
keymap[Qt.Key_Asterisk] = "*"
keymap[Qt.Key_Hash] = "#"

keymap[Qt.Key_Down] = 'arrow_down'
keymap[Qt.Key_Left] = 'arrow_left'
keymap[Qt.Key_Right] = 'arrow_right'
keymap[Qt.Key_Up] = 'arrow_up'


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
        self.grabKeyboard()

    def _stopListening(self):
        self._listening = None

    def keyPressEvent(self, event):
        if not self._listening:
            return super().keyPressEvent(event)

        key_name = keymap[event.key()]
        self.setKeycode(key_name)
        self._stopListening()

        event.accept()
        self.releaseKeyboard()