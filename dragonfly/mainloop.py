from __future__ import print_function

import time
import hive as h


class mainloopclass(object):

    def __init__(self, maxframerate):
        self._hive = h.get_runhive()
        self._running = False
        self._stop = False
        self.maxframerate = maxframerate
        self._listeners = []

    def run(self):
        if self._running:
            return

        self._time = time.time()
        currtime = self._time

        while not self._stop:
            nexttick = currtime + 1.0/self.maxframerate

            self.tick()

            currtime = time.time()

            if currtime < nexttick:
                time.sleep(nexttick-currtime)
                currtime = nexttick

    def stop(self):
        self._stop = True

    def tick(self):
        self._hive.tick()


def build_mainloop(cls, i, ex, args):
    i.tick = h.triggerfunc()
    i.stop = h.triggerable(cls.stop)
    i.run = h.triggerable(cls.run)    


    ex.tick = h.hook(i.tick)
    ex.run = h.entry(i.run)
    ex.stop = h.entry(i.stop)
    ex.maxframerate = h.property(cls, "maxframerate")


mainloop = h.hive("mainloop", build_mainloop, mainloopclass)