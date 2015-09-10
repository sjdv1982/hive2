import hive

from .event import EventListener


class _TickCls:

    def __init__(self):
        self._hive = hive.get_run_hive()

    def add_event_listener(self, add_listener):
        add_listener(EventListener(self.on_tick, ("tick",), mode='match'))

    def on_tick(self):
        self._hive._on_tick()

    def set_quit(self, func):
        self._quit = func


def build_tick(cls, i, ex, args):
    i.on_tick = hive.triggerfunc()
    ex.on_tick = hive.hook(i.on_tick)

    ex.get_event_listener = hive.socket(cls.add_event_listener, ("event", "add_listener"))


Tick = hive.hive("Tick", build_tick, cls=_TickCls)