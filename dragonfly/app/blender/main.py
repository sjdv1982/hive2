import hive

from .input_handler import InputHandler
from .startup_binder import StartupBinder
from .scene import Scene

from ...event import EventHive, EventHandler
from ...mainloop import Mainloop as _Mainloop


class _MainloopCls:

    def __init__(self, max_framerate=60):
        self.bge = __import__("bge")
        self.input_handler = InputHandler()

        self._hive = hive.get_run_hive()
        self._read_event = None

        self._scenes = {s.name: Scene()}

    def on_tick(self):
        self._read_event(("pre_tick",))

        self.bge.logic.NextFrame()
        self.input_handler.update_events()

        self._read_event(("tick",))

    def set_event_dispatcher(self, func):
        # Dispatch events from input handler to event manager
        self.input_handler.add_listener(func)
        self._read_event = func

    def add_listener(self, func):
        # Add input handler
        listener = EventHandler(self.stop, ("keyboard", "pressed", "ESCAPE"), mode='match')
        func(listener)

    def stop(self):
        self._read_event(("quit",))
        self._hive.stop()


def build_mainloop(cls, i, ex, args):
    i.event_manager = EventHive()

    # Get read event
    ex.get_dispatcher = hive.socket(cls.set_event_dispatcher, ("event", "dispatch"))

    # Get add handler
    ex.get_add_handler = hive.socket(cls.add_single_listener, ("event", "add_listener"))

    # Get add handler
    ex.do_quit = hive.plugin(ex.stop, ("quit",))

    i.startup_binder = StartupBinder()

    i.on_tick = hive.triggerable(cls.on_tick)
    hive.trigger(i.tick, i.on_tick)


Mainloop = _Mainloop.extend("Mainloop", build_mainloop, builder_cls=_MainloopCls)
