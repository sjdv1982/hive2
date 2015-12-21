import hive

from ..event import EventHandler


class WatchClass:

    def __init__(self):
        self._last_value = None
        self.current_value = None

        self._hive = hive.get_run_hive()

    def _on_tick(self):
        self._hive.value()

        current_value = self.current_value
        last_value, self._last_value = self._last_value, current_value

        if current_value != last_value:
            self._hive._on_changed()

    def set_add_handler(self, add_handler):
        handler = EventHandler(self._on_tick, ("tick",), mode='match')
        add_handler(handler)


def declare_watch(meta_args):
    meta_args.data_type = hive.parameter("tuple", ("int",))


def build_watch(cls, i, ex, args, meta_args):
    """Watch value and indicate when it is changed.

    Uses a tick callback.
    """
    i.value = hive.property(cls, "current_value", meta_args.data_type)
    i.pull_in = hive.pull_in(i.value)
    ex.value = hive.antenna(i.pull_in)

    i.on_changed = hive.triggerfunc()
    ex.on_changed = hive.hook(i.on_changed)

    ex.get_add_handler = hive.socket(cls.set_add_handler,
                                     identifier=("event", "add_handler"))


Watch = hive.dyna_hive("Watch", build_watch, declare_watch, cls=WatchClass)
