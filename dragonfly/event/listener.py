import hive

from .event import EventHandler


class _ListenerCls:

    @hive.types(event="str", mode="str")
    @hive.options(mode={'leader', 'match', 'trigger'})
    def __init__(self, event, mode='leader'):
        self.add_handler = None
        self.event = event
        self.mode = mode
        self._hive = hive.get_run_hive()

    def on_event(self, tail=None):
        self._hive._on_event()

    def set_add_handler(self, add_handler):
        handler = EventHandler(self.on_event, self.event, mode=self.mode)
        add_handler(handler)


def build_listener(cls, i, ex, args):
    """Tick event sensor, trigger on_tick every tick"""
    i.on_event = hive.triggerfunc()
    ex.on_event = hive.hook(i.on_event)

    ex.get_add_handler = hive.socket(cls.set_add_handler, "event.add_handler")


Listener = hive.hive("Listener", build_listener, cls=_ListenerCls)
