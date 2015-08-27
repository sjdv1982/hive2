import hive


def declare_filter(meta_args):
    meta_args.data_type = hive.parameter("str", "int")


def build_filter(i, ex, args, meta_args):
    ex.value = hive.attribute(meta_args.data_type)

    i.input = hive.pull_in(ex.value)
    ex.input = hive.antenna(i.input)

    i.true = hive.triggerfunc()
    ex.true = hive.hook(i.true)

    i.false = hive.triggerfunc()
    ex.false = hive.hook(i.false)

    i.trigger = hive.modifier(lambda h: h.true() if h.value else h.false())
    ex.trigger = hive.entry(i.trigger)


Filter = hive.dyna_hive("Filter", build_filter, declare_filter)