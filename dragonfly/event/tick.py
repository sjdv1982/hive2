import hive

from .event import EventHandler


class _TickCls:

    def __init__(self):
        self._hive = hive.get_run_hive()

    def set_add_handler(self, add_handler):
        handler = EventHandler(self._hive._on_tick, ("tick",), mode="match")
        add_handler(handler)


def build_tick(cls, i, ex, args):
    """Tick event sensor, trigger on_tick every tick"""
    i.on_tick = hive.triggerfunc()
    ex.on_tick = hive.hook(i.on_tick)

    ex.get_add_handler = hive.socket(cls.set_add_handler, ("event", "add_handler"))


Tick = hive.hive("Tick", build_tick, cls=_TickCls)
