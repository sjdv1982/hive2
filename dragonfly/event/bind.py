import hive

from .event import EventHandler
from ..bind import BindInfo


class EventEnvironmentClass:

    def __init__(self, context):
        self._handlers = []

        self._main_add_handler = context.plugins['event']['add_handler']
        self._main_remove_handler = context.plugins['event']['remove_handler']

        self._hive = hive.get_run_hive()

        event_config = context.config['event']
        forward_events = event_config['forward_events']

        if forward_events == 'by_leader':
            self._leader = event_config['leader']
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
    ex.add_handler = hive.plugin(cls.add_handler, identifier="event.add_handler")
    ex.remove_handler = hive.plugin(cls.remove_handler, identifier="event.remove_handler")
    ex.read_event = hive.plugin(cls.handle_event, identifier="event.process")

    ex.event_on_stopped = hive.plugin(cls.on_closed, identifier="on_stopped", policy=hive.SingleOptional)


EventEnvironment = hive.meta_hive("EventEnvironment", build_event_environment, declare_event_environment,
                                  cls=EventEnvironmentClass)


class EventBindClass:

    def __init__(self):
        self._hive = hive.get_run_hive()

        self._plugins = {}
        self.leader = None

    def set_add_handler(self, add_handler):
        self._plugins['add_handler'] = add_handler

    def set_remove_handler(self, remove_handler):
        self._plugins['remove_handler'] = remove_handler

    def get_plugins(self):
        return {'event': self._plugins}

    def get_config(self):
        meta_args = self._hive._hive_object._hive_meta_args_frozen
        forward_events = meta_args.forward_events

        this_config = {'forward_events': forward_events}
        config = {'event': this_config}

        if forward_events == 'by_leader':
            # Pull leader
            self._hive.leader()
            this_config["leader"] = self.leader

        return config


def declare_bind(meta_args):
    meta_args.forward_events = hive.parameter("str", 'by_leader', {'none', 'by_leader', 'all'})


def build_bind(cls, i, ex, args, meta_args):
    if meta_args.forward_events == 'none':
        return

    if meta_args.forward_events == "by_leader":
        i.event_leader = hive.property(cls, "leader", "tuple")
        i.pull_event_leader = hive.pull_in(i.event_leader)
        ex.event_leader = hive.antenna(i.pull_event_leader)

    ex.event_set_add_handler = hive.socket(cls.set_add_handler, identifier="event.add_handler")
    ex.event_set_remove_handler = hive.socket(cls.set_remove_handler, identifier="event.remove_handler")

    ex.event_get_plugins = hive.plugin(cls.get_plugins, identifier="bind.get_plugins")
    ex.event_get_config = hive.plugin(cls.get_config, identifier="bind.get_config")


BindEvent = hive.dyna_hive("BindEvent", build_bind, declarator=declare_bind, cls=EventBindClass)


def get_environments(meta_args):
    if meta_args.forward_events != 'none':
        return EventEnvironment,

    return ()


bind_info = BindInfo("event", BindEvent, get_environments)
