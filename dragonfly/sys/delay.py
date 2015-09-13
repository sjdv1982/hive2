import hive

from ..event import EventListener


class _DelayCls:

    def __init__(self):
        self.add_handler = None
        self.remove_handler = None
        self.delay = -1

        self._hive = hive.get_run_hive()
        self._listener = None
        self._counter = 0

    def set_add_handler(self, add_handler):
        self.add_handler = add_handler

    def set_remove_handler(self, remove_handler):
        self.remove_handler = remove_handler

    def on_triggered(self):
        assert self.delay > 0, "Delay must be greater than zero"

        if self._listener is None:
            # Create and register listener
            self._listener = listener = EventListener(self.on_tick, ("tick",), mode="match")
            self.add_handler(listener)

        self._counter = self.delay

    def on_elapsed(self):
        # Unregister and forget listener
        self.remove_listener(self._listener)
        self._listener = None

        self._hive._on_elapsed()

    def on_tick(self):
        self._counter -= 1

        if not self._counter:
            self.on_elapsed()


def build_delay(cls, i, ex, args):
    """Delay input trigger by X ticks, where X is the value of delay_in (greater than zero)"""
    i.on_elapsed = hive.triggerfunc()
    ex.on_elapsed = hive.hook(i.on_elapsed)

    i.trig_in = hive.triggerable(cls.on_triggered)
    ex.trig_in = hive.entry(i.trig_in)

    ex.delay = hive.property(cls, "delay", "int", 1)
    i.delay_in = hive.pull_in(ex.delay)
    ex.delay_in = hive.antenna(i.delay_in)

    ex.get_add_handler = hive.socket(cls.set_add_handler, ("event", "add_handler"))
    ex.get_remove_handler = hive.socket(cls.set_remove_handler, ("event", "remove_handler"))


Delay = hive.hive("Delay", build_delay, cls=_DelayCls)