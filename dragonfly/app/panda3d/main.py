import hive

from .input_handler import InputHandler
from .entity_api import EntityAPI

from ..mainloop import Mainloop as _Mainloop
from ...event import EventHive, EventHandler


class MainloopClass:

    def __init__(self, max_framerate=60):
        from direct.showbase.ShowBase import ShowBase

        self.base = ShowBase()
        self._hive = hive.get_run_hive()

        self._read_event = None
        self._add_handler = None

    def on_tick(self):
        self._read_event(("pre_tick",))

        base.taskMgr.step()
        self._hive._input_manager.update()

        self._read_event(("tick",))

    def set_event_dispatcher(self, func):
        # Dispatch events from input handler to event manager
        self._read_event = func

    def set_add_handler(self, add_handler):
        # Add input handler
        self._add_handler = add_handler

    def on_started(self):
        handler = EventHandler(self._hive.stop, ("keyboard", "pressed", "escape"), mode='match')
        self._add_handler(handler)


def build_mainloop(cls, i, ex, args):
    i.event_manager = EventHive(export_namespace=True)
    i.input_manager = InputHandler(export_namespace=True)
    i.entity_api = EntityAPI(export_namespace=True)

    hive.connect(i.input_manager.event, i.event_manager.event_in)

    # Get read event
    ex.get_dispatcher = hive.socket(cls.set_event_dispatcher, "event.process")
    ex.get_add_handler = hive.socket(cls.set_add_handler, "event.add_handler")

    # Add startup and stop callbacks
    ex.main_on_started = hive.plugin(cls.on_started, identifier="on_started")

    i.on_tick = hive.triggerable(cls.on_tick)
    hive.trigger(i.tick, i.on_tick)


Mainloop = _Mainloop.extend("Mainloop", build_mainloop, builder_cls=MainloopClass)