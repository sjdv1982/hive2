import hive

from .input_handler import InputHandler
#from .scene import Scene, Instantiator

from ..mainloop import Mainloop as _Mainloop
from ...event import EventHive, EventHandler


class MainloopClass:

    def __init__(self, max_framerate=60):
        from direct.showbase.ShowBase import ShowBase

        self.base = ShowBase()
        self._hive = hive.get_run_hive()
        self._read_event = None

        self._scenes = {}
        self.bind_id = None

    def on_start(self):
        self._read_event(("start",))

    def on_stop(self):
        self._read_event(("stop",))

    def on_tick(self):
        self._read_event(("pre_tick",))

        base.taskMgr.step()
        self._hive._input_handler.update()

        self._read_event(("tick",))

    def set_event_dispatcher(self, func):
        # Dispatch events from input handler to event manager
        self._read_event = func

    def add_handler(self, add_handler):
        # Add input handler
        handler = EventHandler(self.stop, ("keyboard", "pressed", "escape"), mode='match')
        add_handler(handler)

    def stop(self):
        self._hive.stop()
        self._read_event(("quit",))


def build_mainloop(cls, i, ex, args):
    i.event_manager = EventHive()
    i.input_handler = InputHandler()

    # Scene instantiator
    # i.scene_instantiator = Instantiator(forward_events='all')
    # i.scene_hive_class = Variable("class", Scene)
    # hive.connect(i.scene_hive_class, i.scene_instantiator.hive_class)

    # i.bind_id = hive.property(cls, "bind_id", ("str", "id"))
    # i.pull_bind_id = hive.pull_out(i.bind_id)
    # hive.connect(i.pull_bind_id, i.scene_instantiator.bind_id)

    # Get read event
    ex.get_dispatcher = hive.socket(cls.set_event_dispatcher, ("event", "process"))
    ex.get_add_handler = hive.socket(cls.add_handler, ("event", "add_handler"))

    ex.do_quit = hive.plugin(cls.stop, ("quit",))

    ex.add_on_startup = hive.plugin(cls.on_start, identifier=("callback", "start"))
    ex.add_on_stopped = hive.plugin(cls.on_stop, identifier=("callback", "stop"))

    i.on_tick = hive.triggerable(cls.on_tick)
    hive.trigger(i.tick, i.on_tick)


Mainloop = _Mainloop.extend("Mainloop", build_mainloop, builder_cls=MainloopClass)
