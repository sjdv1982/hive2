import hive

from dragonfly.event import EventHandler


class WatchClass:
    def __init__(self):
        self._last_value = None
        self.current_value = None

        self._hive = hive.get_run_hive()

    def _on_tick(self):
        self._hive.value()

        self.compare_values()

    def compare_values(self):
        current_value = self.current_value
        last_value, self._last_value = self._last_value, current_value

        if current_value != last_value:
            self._hive._on_changed()

    def set_add_handler(self, add_handler):
        handler = EventHandler(self._on_tick, ("tick",), mode='match')
        add_handler(handler)


def declare_watch(meta_args):
    meta_args.data_type = hive.parameter("str", "int")
    meta_args.mode = hive.parameter("str", "pull", {"push", "pull"})


def build_watch(cls, i, ex, args, meta_args):
    """Watch value and indicate when it is changed.

    Uses a tick callback.
    """
    args.start_value = hive.parameter(meta_args.data_type, None)
    i.value = hive.property(cls, "current_value", meta_args.data_type, args.start_value)

    if meta_args.mode == 'pull':
        i.value_in = hive.pull_in(i.value)

    else:
        i.value_in = hive.push_in(i.value)

    ex.value = hive.antenna(i.value_in)

    i.on_changed = hive.triggerfunc()
    ex.on_changed = hive.hook(i.on_changed)

    if meta_args.mode == 'pull':
        ex.get_add_handler = hive.socket(cls.set_add_handler, identifier="event.add_handler")

    else:
        i.compare_values = hive.triggerable(cls.compare_values)
        hive.trigger(i.value_in, i.compare_values)


Watch = hive.dyna_hive("Watch", build_watch, declare_watch, builder_cls=WatchClass)
