import hive

from .event import EventHandler


class _OnQuit:

    def __init__(self):
        self._hive = hive.get_run_hive()

    def set_add_handler(self, add_handler):
        callback = self._hive._on_quit
        handler = EventHandler(callback, ("quit",), mode='match')
        add_handler(handler)


def build_on_quit(cls, i, ex, args):
    """Listen for quit event"""
    ex.get_add_handler = hive.socket(cls.set_add_handler, ("event", "add_handler"))

    i.on_quit = hive.triggerfunc()
    ex.on_quit = hive.hook(i.on_quit)


OnQuit = hive.hive("OnQuit", build_on_quit, cls=_OnQuit)
