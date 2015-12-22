import hive

from .event import EventHandler
from ..bind import BindInfo


class EventEnvironmentClass:

    def __init__(self, context, bind_id):
        self._identifier = bind_id
        self._leader = bind_id,
        self._handlers = []

        self._main_add_handler = context.plugins['event']['add_handler']
        self._main_remove_handler = context.plugins['event']['remove_handler']

        self._hive = hive.get_run_hive()

        configuration = self._hive._hive_object._hive_meta_args_frozen.bind_configuration

        if configuration.event_dispatch_mode == 'by_leader':
            self._main_handler = EventHandler(self.handle_event, self._leader)

        else:
            self._main_handler = EventHandler(self.handle_event, None)

        self._main_add_handler(self._main_handler)

    def add_handler(self, handler):
        self._handlers.append(handler)

    def remove_handler(self, handler):
        self._handlers.remove(handler)

    def handle_event(self, event):
        for handler in self._handlers:
            handler(event)

    def on_closed(self):
        """Disconnect from external event stream"""
        self._main_remove_handler(self._main_handler)


def declare_event_environment(meta_args):
    pass


def build_event_environment(cls, i, ex, args, meta_args):
    """Runtime event environment for instantiated hive.

    Provides appropriate sockets and plugins for event interface
    """
    ex.add_handler = hive.plugin(cls.add_handler, identifier=("event", "add_handler"))
    ex.remove_handler = hive.plugin(cls.remove_handler, identifier=("event", "remove_handler"))
    ex.read_event = hive.plugin(cls.handle_event, identifier=("event", "process"))
    ex.event_closer = hive.plugin(cls.on_closed, identifier=("bind", "add_closer"), policy=hive.SingleRequired)

EventEnvironment = hive.meta_hive("EventEnvironment", build_event_environment, declare_event_environment,
                                  cls=EventEnvironmentClass)


class EventBindClass:

    def __init__(self):
        self._hive = hive.get_run_hive()

        self._add_handler = None
        self._remove_handler = None

    def set_add_handler(self, add_handler):
        self._add_handler = add_handler

    def set_remove_handler(self, remove_handler):
        self._remove_handler = remove_handler

    def get_plugins(self):
        return {'event': {'add_handler': self._add_handler, 'remove_handler': self._remove_handler}}

    def get_config(self):
        dispatch_mode = self._hive._hive_object._hive_meta_args_frozen.event_dispatch_mode
        return {'event': {'dispatch_mode': dispatch_mode}}


def declare_bind(meta_args):
    meta_args.bind_event = hive.parameter("bool", True)
    meta_args.event_dispatch_mode = hive.parameter("str", 'by_leader', {'by_leader', 'all'})


def build_bind(cls, i, ex, args, meta_args):
    if not meta_args.bind_event:
        return

    ex.event_set_add_handler = hive.socket(cls.set_add_handler, identifier=("event", "add_handler"))
    ex.event_set_remove_handler = hive.socket(cls.set_remove_handler, identifier=("event", "remove_handler"))
    ex.event_get_plugins = hive.plugin(cls.get_plugins, identifier=("bind", "get_plugins"))
    ex.event_get_config = hive.plugin(cls.get_config, identifier=("bind", "get_config"))


BindEvent = hive.dyna_hive("BindEvent", build_bind, declarator=declare_bind, cls=EventBindClass)


def is_enabled(meta_args):
    return meta_args.bind_event


bind_info = BindInfo("event", is_enabled, BindEvent, EventEnvironment)