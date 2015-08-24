import hive
import string


def declare_trigger(args):
    args.count = hive.parameter("int", 1, options=set(range(26)))


def build_trigger(i, ex, args):
    """Collapse multiple trigger inputs to single trigger output"""
    def trigger(self):
        self._trigger()

    i.on_triggered = hive.modifier(trigger)
    i.trigger = hive.triggerfunc()
    ex.trig_out = hive.hook(i.trigger)

    for index, char in zip(range(args.count), string.ascii_lowercase):
        setattr(ex, char, hive.entry(i.on_triggered))


Trigger = hive.hive("Trigger", build_trigger, declarator=declare_trigger)
