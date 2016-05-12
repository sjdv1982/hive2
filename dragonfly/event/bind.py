from weakref import WeakValueDictionary

import hive
from .event import EventHandler, EventDispatcher
from ..bind import BindInfo, BindClassDefinition


definition = BindClassDefinition()
forward_events = definition.parameter("forward_events", "str", 'by_leader', {'none', 'by_leader', 'all'})

with definition.condition(forward_events != "none"):
    definition.forward_plugin("event.add_handler", declare_for_environment=False)
    definition.forward_plugin("event.remove_handler", declare_for_environment=False)


factory = definition.build("BindEvent")


class EventBindClass(factory.create_external_class()):

    def __init__(self):
        super().__init__()

        self._hive = hive.get_run_hive()
        self.leader = None

        self._processes = WeakValueDictionary()

    def on_created(self, process_id, environment_hive):
        self._processes[process_id] = environment_hive

    @hive.types(process_id="int")
    def pause(self, process_id):
        self._processes[process_id].pause_events()

    @hive.types(process_id="int")
    def resume(self, process_id):
        self._processes[process_id].resume_events()

    def get_config(self):
        if hasattr(self._hive, "event_leader"):
            # Pull leader
            self._hive.event_leader()
            dict(leader=self.leader)

        return {}


@factory.builds_external
def build_bind(cls, i, ex, args, meta_args):
    if meta_args.forward_events == "none":
        return

    if meta_args.forward_events == "by_leader":
        i.event_leader = hive.property(cls, "leader", "tuple")
        i.pull_event_leader = hive.pull_in(i.event_leader)
        ex.event_leader = hive.antenna(i.pull_event_leader)

    i.push_pause_in = hive.push_in(cls.pause)
    ex.pause_events = hive.antenna(i.push_pause_in)

    i.push_resume_in = hive.push_in(cls.resume)
    ex.resume_events = hive.antenna(i.push_resume_in)

    ex.on_created = hive.plugin(cls.on_created, "bind.on_created")


_BindEvent = hive.dyna_hive("BindEvent", build_bind, declarator=factory.external_declarator, builder_cls=EventBindClass)


class EventEnvironmentClass(factory.create_environment_class()):

    def __init__(self, context):
        super().__init__(context)

        self._dispatcher = EventDispatcher()
        self._hive = hive.get_run_hive()

        self._main_add_handler = context.plugins['event.add_handler']
        self._main_remove_handler = context.plugins['event.remove_handler']

        self._can_process_events = True

        leader = context.config.get('leader', None)
        self._main_handler = EventHandler(self.handle_event, leader)
        self._handler_is_registered = False

    def _update_listener_state(self):
        has_handlers = self._dispatcher.has_handlers

        needs_unregistration = not (has_handlers and self._can_process_events) and self._handler_is_registered
        needs_registration = has_handlers and self._can_process_events and not self._handler_is_registered

        if needs_registration:
            self._main_add_handler(self._main_handler)
            self._handler_is_registered = True

        elif needs_unregistration:
            self._main_remove_handler(self._main_handler)
            self._handler_is_registered = False

    def pause(self):
        assert self._can_process_events
        self._can_process_events = False

        self._update_listener_state()

    def resume(self):
        assert not self._can_process_events
        self._can_process_events = True

        self._update_listener_state()

    def add_handler(self, handler):
        self._dispatcher.add_handler(handler)
        self._update_listener_state()

    def remove_handler(self, handler):
        self._dispatcher.remove_handler(handler)
        self._update_listener_state()

    def handle_event(self, event):
        self._dispatcher.handle_event(event)

    def on_closed(self):
        """Disconnect from external event stream"""
        self._dispatcher.clear_handlers()

        self._update_listener_state()


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

    i.pause_events = hive.triggerable(cls.pause)
    ex.pause_events = hive.entry(i.pause_events)

    i.resume_events = hive.triggerable(cls.resume)
    ex.resume_events = hive.entry(i.resume_events)


_EventEnvironment = hive.meta_hive("EventEnvironment", build_event_environment, declare_event_environment,
                                  builder_cls=EventEnvironmentClass)


def get_environment(meta_args):
    if meta_args.forward_events != 'none':
        return _EventEnvironment

    return None


bind_info = BindInfo(factory.name, _BindEvent, get_environment)
