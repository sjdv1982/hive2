import hive

from ..std import Buffer


def build_cycle(i, ex, args):
    ex.period = hive.attribute("int", 0)
    ex.counter = hive.attribute("int", 0)

    i.period_in = hive.pull_in(ex.period)
    ex.period_in = hive.antenna(i.period_in)
    ex.input = hive.entry(i.period_in)

    def cycle(self):
        self.counter += 1

        if self.counter >= self.period_in:
            self.counter -= self.period_in
            self.output()

    i.trigger = hive.modifier(cycle)
    hive.trigger(i.period_in, i.trigger)

    i.output = hive.triggerfunc()
    ex.output = hive.hook(i.output)


Cycle = hive.hive("Cycle", build_cycle)
