import hive

from ...mainloop import Mainloop as _Mainloop
from ...event import EventHive, EventListener
from .input_handler import InputHandler


class Mainloop:

    def __init__(self, max_framerate=60):
        self.bge = __import__("bge")
        self.input_handler = InputHandler()

        self._hive = hive.get_run_hive()

    def on_tick(self):
        self.read_event(("pre_tick",))

        self.bge.logic.NextFrame()
        self.input_handler.update_events()

        self.read_event(("tick",))

    def set_event_processor(self, func):
        self.input_handler.add_listener(func)
        self.read_event = func

    def add_listener(self, func):
        # Add input handler
        listener = EventListener(self.stop, ("keyboard", "pressed", "ESCAPE"), mode='match')
        func(listener)

    def stop(self):
        self._hive.stop()


def build_mainloop(cls, i, ex, args):
    i.event_manager = EventHive()

    i.on_tick = hive.triggerable(cls.on_tick)
    hive.trigger(i.tick, i.on_tick)

    # Get read event
    ex.event_reader = hive.socket(cls.set_event_processor)
    hive.connect(i.event_manager.read_event, ex.event_reader)

    # Get add handler
    ex.on_quit = hive.socket(cls.add_listener)
    hive.connect(i.event_manager.add_handler, ex.on_quit)


Mainloop = _Mainloop.extend("Mainloop", build_mainloop, builder_cls=Mainloop)