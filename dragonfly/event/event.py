import hive


def match_leader(event, leader):
    event_leader = event[:len(leader)]

    if event_leader != leader:
        return None

    return event[len(leader):]


class EventHandler:

    def __init__(self, callback, pattern=None, priority=0, mode='leader'):
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
        self.handlers = []

    def add_handler(self, handler):
        self.handlers.append(handler)
        self.handlers.sort()

    def remove_handler(self, handler):
        self.handlers.remove(handler)
        self.handlers.sort()

    def handle_event(self, event):
        for handler in self.handlers:
            handler(event)


def event_builder(cls, i, ex, args):
    ex.add_handler = hive.plugin(cls.add_handler, identifier=("event", "add_handler"), export_to_parent=True)
    ex.remove_handler = hive.plugin(cls.remove_handler, identifier=("event", "remove_handler"), export_to_parent=True)
    ex.read_event = hive.plugin(cls.handle_event, identifier=("event", "process"), export_to_parent=True)


EventHive = hive.hive("EventHive", event_builder, EventManager)


