from __future__ import print_function

import time

import hive


class _Mainloop(object):

    @hive.argument_types(max_framerate=('int',))
    def __init__(self, max_framerate=60):
        self._hive = hive.get_run_hive()
        self.max_framerate = max_framerate

        self._running = True
        self._listeners = []

        # Callbacks
        self._startup_callbacks = []
        self._stop_callbacks = []

    def add_startup_callback(self, callback):
        self._startup_callbacks.append(callback)

    def add_stop_callback(self, callback):
        self._stop_callbacks.append(callback)

    def run(self):
        for callback in self._startup_callbacks:
            callback()

        accumulator = 0.0
        last_time = time.clock()

        while self._running:
            current_time = time.clock()
            elapsed_time = current_time - last_time
            last_time = current_time

            if elapsed_time > 0.25:
                elapsed_time = 0.25

            accumulator += elapsed_time
            while accumulator > (1. / self.max_framerate):
                accumulator -= 1. / self.max_framerate
                self.tick()

    def stop(self):
        self._running = False

        for callback in self._stop_callbacks:
            callback()

    def tick(self):
        self._hive.tick()


def build_mainloop(cls, i, ex, args):
    i.tick = hive.triggerfunc()
    i.stop = hive.triggerable(cls.stop)
    i.run = hive.triggerable(cls.run)

    ex.tick = hive.hook(i.tick)
    ex.run = hive.entry(i.run)
    ex.stop = hive.entry(i.stop)
    ex.max_framerate = hive.property(cls, "max_framerate")

    # Startup / End callback
    ex.add_startup_callback = hive.socket(cls.add_startup_callback, ("callback", "start"), policy=hive.MultipleOptional)
    ex.add_stop_callback = hive.socket(cls.add_stop_callback, ("callback", "stop"), policy=hive.MultipleOptional)


Mainloop = hive.hive("mainloop", build_mainloop, _Mainloop)