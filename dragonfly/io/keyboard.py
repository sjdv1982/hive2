import hive

from ..event import EventListener


class Keyboard_:

    def __init__(self):
        self._hive = hive.get_run_hive()
        self.key = None

        self._pressed_listener = None
        self._released_listener = None

    def add_listener(self, func):
        self._pressed_listener = EventListener(self._hive._on_pressed, ("keyboard", "pressed", self.key))
        func(self._pressed_listener)

        self._released_listener = EventListener(self._hive._on_released, ("keyboard", "released", self.key))
        func(self._released_listener)

    def update_listeners(self):
        self._pressed_listener.pattern = ("keyboard", "pressed", self.key)
        self._released_listener.pattern = ("keyboard", "released", self.key)


def build_keyboard(cls, i, ex, args):
    ex.on_event = hive.socket(cls.add_listener, identifier=("event", "add_listener"))
    i.on_tick = hive.triggerfunc()

    i.key = hive.property(cls, "key", "str", "w")

    i.key_in = hive.pull_in(i.key)
    ex.key_in = hive.antenna(i.key_in)

    i.on_key_changed = hive.triggerable(cls.update_listeners)
    hive.trigger(i.key_in, i.on_key_changed)

    i.on_pressed = hive.triggerfunc()
    ex.on_pressed = hive.hook(i.on_pressed)

    i.on_released = hive.triggerfunc()
    ex.on_released = hive.hook(i.on_released)


Keyboard = hive.hive("Keyboard", build_keyboard, cls=Keyboard_)
