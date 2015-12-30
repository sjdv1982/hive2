import string
from functools import partial

import hive


keyboard_mapping = {'lcontrol': 'left_control', 'lshift': 'left_shift', 'ralt': 'right_alt', 'rcontrol': 'right_control',
               'lalt': 'left_alt', 'space': 'space', 'escape': 'escape', 'home': 'home', 'insert': 'insert',
               'backspace': 'backspace', 'shift': 'shift', 'rshift': 'right_shift', 'page_up': 'page_up',
               'page_down': 'page_down', 'tab': 'tab', 'delete': 'delete', 'end': 'end', 'enter': 'enter',
               'arrow_up': 'arrow_up', 'arrow_down': 'arrow_down', 'arrow_left': 'arrow_left',
               'arrow_right': 'arrow_right'}

keyboard_mapping.update({x: x for x in string.digits})
keyboard_mapping.update(zip(string.ascii_lowercase, string.ascii_lowercase))

mouse_mapping = {'mouse1': 'left', 'mouse2': 'middle', 'mouse3': 'right',
                 'wheel_up': 'wheel_up', 'wheel_down': 'wheel_down'}


class InputHandlerClass:

    def __init__(self):
        from direct.showbase.DirectObject import DirectObject
        self._obj = DirectObject()

        for event_name, remapped_name in keyboard_mapping.items():
            self._obj.accept(event_name, partial(self.broadcast_event, ("keyboard", "pressed", remapped_name)))
            self._obj.accept("{}-up".format(event_name), partial(self.broadcast_event,
                                                                 ("keyboard", "released", remapped_name)))

        for event_name, remapped_name in mouse_mapping.items():
            self._obj.accept(event_name, partial(self.broadcast_event, ("mouse", "pressed", remapped_name)))
            self._obj.accept("{}-up".format(event_name), partial(self.broadcast_event,
                                                                 ("mouse", "released", remapped_name)))

        self._mouse_pos = None
        self.event = None

        self._hive = hive.get_run_hive()

    def set_read_event(self, read_event):
        self._read_event = read_event

    def broadcast_event(self, event):
        self.event = event
        self._hive.event()

    def update(self):
        if base.mouseWatcherNode.hasMouse():
            x = base.mouseWatcherNode.getMouseX()
            y = base.mouseWatcherNode.getMouseY()

            mouse_pos = x, y

            if mouse_pos != self._mouse_pos:
                self._mouse_pos = mouse_pos
                self.broadcast_event(("mouse", "move", mouse_pos))


def build_input_handler(cls, i, ex, args):
    i.update = hive.triggerable(cls.update)
    ex.update = hive.entry(i.update)

    i.event = hive.property(cls, "event", "tuple")
    i.push_event = hive.push_out(i.event)
    ex.event = hive.output(i.push_event)


InputHandler = hive.hive("InputHandler", build_input_handler, InputHandlerClass)
