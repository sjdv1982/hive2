import time

import hive
from ..event import EventHandler


class TimeClass:

    def __init__(self):
        self.start_time = None
        self.elapsed = 0.0

    def on_started(self):
        self.start_time = time.clock()

    def on_tick(self):
        self.elapsed = time.clock() - self.start_time

    def set_add_startup_callback(self, add_callback):
        add_callback(self.on_started)

    def set_add_handler(self, add_handler):
        handler = EventHandler(self.on_tick, ("tick",), mode="match")
        add_handler(handler)


def time_builder(cls, i, ex, args):
    """Access to Python time module"""
    i.elapsed = hive.property(cls, 'elapsed', 'float')
    i.elapsed_out = hive.pull_out(i.elapsed)
    ex.elapsed_out = hive.output(i.elapsed_out)

    ex.add_startup_callback = hive.socket(cls.set_add_startup_callback, ("callback", "startup"))
    ex.get_add_handler = hive.socket(cls.set_add_handler, ("event", "add_handler"))


Time = hive.hive("Time", builder=time_builder, cls=TimeClass)