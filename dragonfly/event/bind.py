import hive

from .event import EventHandler
from ..bind import BindInfo, BindClassDefinition


definition = BindClassDefinition()
forward_events = definition.parameter("forward_events", "str", 'by_leader', {'none', 'by_leader', 'all'})

with definition.condition(forward_events != "none"):
    definition.forward_plugin("event.add_handler", declare_for_environment=False)
    definition.forward_plugin("event.remove_handler", declare_for_environment=False)

factory = definition.build("BindEvent")


class EventBindClass(factory.external_class):

    def __init__(self):
        super().__init__()

        self._hive = hive.get_run_hive()
        self.leader = None

    def get_config(self):
        config = {}
        if hasattr(self._hive, "event_leader"):
            # Pull leader
            self._hive.event_leader()
            config["leader"] = self.leader

        return config


@factory.builds_external
def build_bind(cls, i, ex, args, meta_args):
    if meta_args.forward_events == "by_leader":
        i.event_leader = hive.property(cls, "leader", "tuple")
        i.pull_event_leader = hive.pull_in(i.event_leader)
        ex.event_leader = hive.antenna(i.pull_event_leader)


BindEvent = hive.dyna_hive("BindEvent", build_bind, declarator=factory.external_declarator, cls=EventBindClass)


class EventEnvironmentClass(factory.environment_class):

    def __init__(self, context):
        super().__init__(context)

        self._handlers = []
        self._hive = hive.get_run_hive()

        self._main_add_handler = context.plugins['event.add_handler']
        self._main_remove_handler = context.plugins['event.remove_handler']

        if "leader" in context.config:
            self._leader = context.config['leader']
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


@factory.builds_environment
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


def get_environment(meta_args):
    if meta_args.forward_events != 'none':
        return EventEnvironment

    return None


bind_info = BindInfo(factory.name, BindEvent, get_environment)
