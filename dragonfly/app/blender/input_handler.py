import string

named_keyboard_mapping = dict(ZERO='0', ONE='1', TWO='2', THREE='3', FOUR='4', FIVE='5', SIX='6', SEVEN='7', EIGHT='8',
                              NINE='9', ACCENTGRAVE='`', BACKSLASH='\\', COMMA=',', PERIOD='.', DEL='DELETE', MINUS='-',
                              PLUS='+', LEFTBRACKET='[', RIGHTBRACKET=']', ESC='ESCAPE', END='END', INSERT='INSERT',
                              PAUSE='PAUSE', SEMICOLON=';', SLASH='/', SPACE='SPACE', TAB='TAB', QUOTE="'",
                              PAGEDOWN='PAGEDOWN', PAGEUP='PAGEUP',
                              )
named_keyboard_mapping.update({k: k for k in string.ascii_uppercase})

named_mouse_mapping = dict(LEFTMOUSE='LEFT', MIDDLEMOUSE='MIDDLE', RIGHTMOUSE='RIGHT')


class InputHandler:

    def __init__(self):
        self.bge = __import__("bge")
        self.keyboard = self.bge.logic.keyboard
        self.mouse = self.bge.logic.mouse

        self.keyboard_map = {v: named_keyboard_mapping[k.replace("KEY", "")] for k, v in self.bge.events.__dict__.items()
                             if k.replace("KEY", "") in named_keyboard_mapping}
        self.mouse_map = {v: named_mouse_mapping[k] for k, v in self.bge.events.__dict__.items() if k in named_mouse_mapping}

        self.JUST_PRESSED = self.bge.logic.KX_INPUT_JUST_ACTIVATED
        self.JUST_RELEASED = self.bge.logic.KX_INPUT_JUST_RELEASED
        self.ACTIVE = self.bge.logic.KX_INPUT_ACTIVE

        self._mouse_pos = None

        self.listeners = set()

    def add_listener(self, listener):
        self.listeners.add(listener)

    def broadcast_event(self, event):
        for listener in self.listeners:
            listener(event)

    def update_events(self):
        is_pressed = self.JUST_PRESSED
        is_released = self.JUST_RELEASED

        for key_code, status in self.keyboard.events.items():
            try:
                key_name = self.keyboard_map[key_code]
            except KeyError:
                continue

            if status == is_pressed:
                event = ("keyboard", "pressed", key_name)

            elif status == is_released:
                event = ("keyboard", "released", key_name)

            else:
                continue

            self.broadcast_event(event)

        for key_code, status in self.mouse.events.items():
            try:
                key_name = self.mouse_map[key_code]

            except KeyError:
                continue

            if status == is_pressed:
                event = ("mouse", "pressed", key_name)

            elif status == is_released:
                event = ("mouse", "released", key_name)

            else:
                continue

            self.broadcast_event(event)

        # Broadcast mouse pos
        mouse_pos = self.mouse.position[0], 1 - self.mouse.position[1]
        if mouse_pos != self._mouse_pos:
            self._mouse_pos = mouse_pos
            self.broadcast_event(("mouse", "move", mouse_pos))
