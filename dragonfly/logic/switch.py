import hive


def declare_switch(meta_args):
    meta_args.data_type = hive.parameter("str", "int")


def evaluate_switch(self):
    self.input.pull()

    if self.switch:
        self._true()

    else:
        self._false()


def build_switch(i, ex, args, meta_args):
    """Redirect input trigger to true / false outputs according to boolean evaluation of switch value"""
    ex.switch = hive.attribute(meta_args.data_type)

    i.input = hive.pull_in(ex.switch)
    ex.input = hive.antenna(i.input)

    i.true = hive.triggerfunc()
    ex.true = hive.hook(i.true)

    i.false = hive.triggerfunc()
    ex.false = hive.hook(i.false)

    i.trigger = hive.modifier(evaluate_switch)
    ex.trigger = hive.entry(i.trigger)


Switch = hive.dyna_hive("Switch", build_switch, declare_switch)
