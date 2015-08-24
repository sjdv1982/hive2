import hive

from ..event import EventListener


class Keyboard_:

    def __init__(self):
        self._hive = hive.get_run_hive()
        self.key = None

    def on_key(self, event_tail):
        key, *_ = event_tail

        if key == self.key:
            self._hive.on_pressed()

    def add_listener(self, func):
        listener = EventListener(self.on_key, ("event", "keyboard", "pressed"))
        func(listener)


def build_keyboard(cls, i, ex, args):
    ex.on_event = hive.socket(cls.add_listener, identifier=("event", "add_handler"), auto_connect=True)
    i.on_tick = hive.triggerfunc()

    ex.name = hive.attribute(("str",), "<Sensor>")
    ex.key = hive.property(cls, "key", "str")

    i.key_in = hive.pull_in(ex.key)
    ex.key_in = hive.antenna(i.key_in)

    i.on_pressed = hive.triggerfunc()
    ex.on_pressed = hive.hook(i.on_pressed)


Keyboard = hive.hive("Keyboard", build_keyboard, cls=Keyboard_)