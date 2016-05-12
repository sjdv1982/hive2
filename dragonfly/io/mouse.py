import hive

from ..event import EventHandler


class Mouse_:

    def __init__(self):
        self._hive = hive.get_run_hive()
        self.button = None

        self._pressed_listener = None
        self._released_listener = None

        self.pos_x = 0.0
        self.pos_y = 0.0

        self.dx = 0.0
        self.dy = 0.0

        self.is_pressed = False

    def _on_button_down(self):
        self.is_pressed = True
        self._hive._on_pressed()

    def _on_button_up(self):
        self.is_pressed = False
        self._hive._on_released()

    def on_moved(self, leader):
        old_x = self.pos_x
        old_y = self.pos_y
        pos_x, pos_y = leader[0]

        self.pos_x = pos_x
        self.pos_y = pos_y

        self.dx = pos_x - old_x
        self.dy = pos_y - old_y

        self._hive._on_moved()

    def get_pattern(self, state):
        return "mouse", state, self.button.lower()

    def set_add_handler(self, add_handler):
        moved_listener = EventHandler(self.on_moved, ("mouse", "move"))
        add_handler(moved_listener)

        self._pressed_listener = EventHandler(self._on_button_down, self.get_pattern("pressed"), mode='match')
        add_handler(self._pressed_listener)

        self._released_listener = EventHandler(self._on_button_up, self.get_pattern("released"), mode='match')
        add_handler(self._released_listener)

    def change_listener_buttons(self):
        self._pressed_listener.pattern = self.get_pattern("pressed")
        self._released_listener.pattern = self.get_pattern("released")


def build_mouse(cls, i, ex, args):
    ex.on_event = hive.socket(cls.set_add_handler, identifier="event.add_handler")
    i.on_tick = hive.triggerfunc()

    args.button = hive.parameter("str", "left", options={"left", "middle", "right"})
    i.button = hive.property(cls, "button", "str", args.button)

    i.push_button = hive.push_in(i.button)
    ex.button = hive.antenna(i.push_button)

    i.on_button_changed = hive.triggerable(cls.change_listener_buttons)
    hive.trigger(i.push_button, i.on_button_changed)

    i.on_pressed = hive.triggerfunc()
    ex.on_pressed = hive.hook(i.on_pressed)

    i.on_moved = hive.triggerfunc()
    ex.on_moved = hive.hook(i.on_moved)

    i.pos_x = hive.property(cls, "pos_x", "float")
    i.pull_x = hive.pull_out(i.pos_x)
    ex.x = hive.output(i.pull_x)

    i.pos_y = hive.property(cls, "pos_y", "float")
    i.pull_y = hive.pull_out(i.pos_y)
    ex.y = hive.output(i.pull_y)

    i.dx = hive.property(cls, "dx", "float")
    i.pull_dx = hive.pull_out(i.dx)
    ex.dx = hive.output(i.pull_dx)

    i.dy = hive.property(cls, "dy", "float")
    i.pull_dy = hive.pull_out(i.dy)
    ex.dy = hive.output(i.pull_dy)

    i.is_pressed = hive.property(cls, "is_pressed", "bool")
    i.pull_is_pressed = hive.pull_out(i.is_pressed)
    ex.is_pressed = hive.output(i.pull_is_pressed)


Mouse = hive.hive("Mouse", build_mouse, builder_cls=Mouse_)
