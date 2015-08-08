import hive


def declare_buffer(args):
    args.data_type = hive.parameter("str", "int")
    args.start_value = hive.parameter("int", 0)
    args.mode = hive.parameter("str", "push")


def build_buffer(i, ex, args):
    ex.value = hive.attribute(args.data_type, args.start_value)

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

    else:
        raise ValueError("Buffer mode must be pull or push, not '{}'".format(args.mode))


Buffer = hive.hive("Buffer", build_buffer, declarator=declare_buffer)