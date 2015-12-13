import hive

from ..event import EventHandler


class Keyboard_:

    def __init__(self):
        self._hive = hive.get_run_hive()
        self.key = None

        self._pressed_listener = None
        self._released_listener = None

        self.key_pressed = None
        self.key_released = None

    def add_single_listener(self, func):
        self._pressed_listener = EventHandler(self._hive._on_pressed, ("keyboard", "pressed", self.key))
        func(self._pressed_listener)

        self._released_listener = EventHandler(self._hive._on_released, ("keyboard", "released", self.key))
        func(self._released_listener)

    def add_any_listener(self, func):
        self._pressed_listener = EventHandler(self._on_key_pressed, ("keyboard", "pressed"))
        func(self._pressed_listener)

        self._released_listener = EventHandler(self._on_key_released, ("keyboard", "released"))
        func(self._released_listener)

    def _on_key_pressed(self, trailing):
        self.key_pressed = trailing[0]
        self._hive.key_pressed.push()

    def _on_key_released(self, trailing):
        self.key_released = trailing[0]
        self._hive.key_released.push()

    def change_listeners_key(self):
        self._pressed_listener.pattern = ("keyboard", "pressed", self.key)
        self._released_listener.pattern = ("keyboard", "released", self.key)


def declare_keyboard(meta_args):
    meta_args.mode = hive.parameter("str", options={'single key', 'any key'})


def build_keyboard(cls, i, ex, args, meta_args):
    """Listen for keyboard event"""
    if meta_args.mode == 'single key':
        ex.on_event = hive.socket(cls.add_single_listener, identifier=("event", "add_handler"))

        args.key = hive.parameter("str", "w")
        i.key = hive.property(cls, "key", "str", args.key)

        i.key_in = hive.push_in(i.key)
        ex.key_in = hive.antenna(i.key_in)

        i.on_key_changed = hive.triggerable(cls.change_listeners_key)
        hive.trigger(i.key_in, i.on_key_changed)

        i.on_pressed = hive.triggerfunc()
        ex.on_pressed = hive.hook(i.on_pressed)

        i.on_released = hive.triggerfunc()
        ex.on_released = hive.hook(i.on_released)

    else:
        ex.on_event = hive.socket(cls.add_any_listener, identifier=("event", "add_handler"))

        i.key_pressed = hive.property(cls, 'key_pressed', data_type='str')
        i.key_pressed_out = hive.push_out(i.key_pressed)
        ex.key_pressed = hive.output(i.key_pressed_out)

        i.key_released = hive.property(cls, 'key_released', data_type='str')
        i.key_released_out = hive.push_out(i.key_released)
        ex.key_released = hive.output(i.key_released_out)


Keyboard = hive.dyna_hive("Keyboard", build_keyboard, declarator=declare_keyboard, cls=Keyboard_)
