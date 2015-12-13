import hive


def declare_transistor(meta_args):
    meta_args.data_type = hive.parameter("tuple", ("int",))


def build_transistor(i, ex, args, meta_args):
    """Convert a pull output into a push output using a trigger input"""
    i.in_value = hive.attribute(meta_args.data_type)
    i.input = hive.pull_in(i.in_value)
    ex.input = hive.antenna(i.input)

    i.output = hive.push_out(i.in_value)
    ex.output = hive.output(i.output)

    i.trigger = hive.triggerfunc()
    ex.trigger = hive.entry(i.input)

    hive.trigger(i.input, i.output)


Transistor = hive.dyna_hive("Transistor", build_transistor, declare_transistor)
