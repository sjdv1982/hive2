import hive

from ..std import Buffer


def build_cycle(i, ex, args):
    ex.b_period = Buffer("int", 0)
    ex.period = hive.antenna(ex.b_period.input)

    ex.counter = hive.attribute("int", 0)
    ex.input = hive.entry(ex.b_period.trigger)

    def cycle(self):
        self.counter += 1

        if self.counter >= self.b_period.value:
            self.counter -= self.b_period.value
            self.output()

    i.trigger = hive.modifier(cycle)
    hive.trigger(ex.b_period.output, i.trigger)

    i.output = hive.triggerfunc()
    ex.output = hive.hook(i.output)


Cycle = hive.hive("Cycle", build_cycle)