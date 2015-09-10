from hive.plugin_policies import MultipleOptional
import hive

from dragonfly.std import Buffer


def match_leader(event, leader):
    event_leader = event[:len(leader)]

    if event_leader != leader:
        return None

    return event[len(leader):]


class EventListener:

    def __init__(self, callback, pattern, priority=0, mode='leader'):
        self.callback = callback
        self.pattern = pattern
        self.priority = priority
        self.mode = mode

    def __lt__(self, other):
        return self.priority < other.priority

    def __call__(self, event):
        pattern = self.pattern

        if not pattern:
            self.callback(event)

        else:
            mode = self.mode
            if mode == "leader":
                tail = match_leader(event, pattern)

                if tail is not None:
                    self.callback(tail)

            elif mode == "match":
                if event == pattern:
                    self.callback()

            elif mode == "trigger":
                if match_leader(event, pattern) is not None:
                    self.callback()


class EventManager:

    def __init__(self):
        self.listeners = []

    def add_listener(self, listener):
        self.listeners.append(listener)
        self.listeners.sort()

    def dispatch_event(self, event):
        for listener in self.listeners:
            listener(event)


def event_builder(cls, i, ex, args):
    ex.dispatch_event = hive.plugin(cls.dispatch_event, identifier=("event", "dispatch"), policy_cls=MultipleOptional,
                                    export_to_parent=True)
    ex.add_listener = hive.plugin(cls.add_listener, identifier=("event", "add_listener"), policy_cls=MultipleOptional,
                                  export_to_parent=True)


EventHive = hive.hive("EventHive", event_builder, EventManager)