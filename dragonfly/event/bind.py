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

        if configuration.bind_event == 'by_leader':
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

        self._plugins = {}

    def set_add_handler(self, add_handler):
        self._plugins['add_handler'] = add_handler

    def set_remove_handler(self, remove_handler):
        self._plugins['remove_handler'] = remove_handler

    def get_plugins(self):
        return {'event': self._plugins}

    def get_config(self):
        meta_args = self._hive._hive_object._hive_meta_args_frozen
        bind_event = meta_args.bind_event
        return {'event': {'bind_event': bind_event}}


def is_enabled(meta_args):
    return meta_args.bind_event != 'none'


def declare_bind(meta_args):
    meta_args.bind_event = hive.parameter("str", 'by_leader', {'none', 'by_leader', 'all'})


def build_bind(cls, i, ex, args, meta_args):
    if not is_enabled(meta_args):
        return

    ex.event_set_add_handler = hive.socket(cls.set_add_handler, identifier=("event", "add_handler"))
    ex.event_set_remove_handler = hive.socket(cls.set_remove_handler, identifier=("event", "remove_handler"))
    ex.event_get_plugins = hive.plugin(cls.get_plugins, identifier=("bind", "get_plugins"))
    ex.event_get_config = hive.plugin(cls.get_config, identifier=("bind", "get_config"))


BindEvent = hive.dyna_hive("BindEvent", build_bind, declarator=declare_bind, cls=EventBindClass)


bind_info = BindInfo("event", is_enabled, BindEvent, EventEnvironment)