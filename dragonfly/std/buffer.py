import hive


def declare_buffer(meta_args):
    meta_args.data_type = hive.parameter("str", "int")
    meta_args.start_value = hive.parameter("int", 0)
    meta_args.mode = hive.parameter("str", "push", options={'push', 'pull'})


def build_buffer(i, ex, args, meta_args):
    args.start_value = hive.parameter(meta_args.data_type)
    ex.value = hive.attribute(meta_args.data_type, args.start_value)

    if args.mode == "push":
        i.input = hive.push_in(ex.value)
        ex.input = hive.antenna(i.input)

        i.output = hive.push_out(ex.value)
        ex.output = hive.output(i.output)

        i.trigger = hive.triggerable(i.output)
        ex.trigger = hive.entry(i.trigger)

    elif args.mode == "pull":
        i.input = hive.pull_in(ex.value)
        ex.input = hive.antenna(i.input)

        i.output = hive.pull_out(ex.value)
        ex.output = hive.output(i.output)

        i.trigger = hive.triggerable(i.input)
        ex.trigger = hive.entry(i.trigger)


Buffer = hive.dyna_hive("Buffer", build_buffer, declarator=declare_buffer)