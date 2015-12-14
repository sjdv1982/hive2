import hive


def declare_buffer(meta_args):
    meta_args.data_type = hive.parameter("tuple", ("int",))
    meta_args.mode = hive.parameter("str", "push", options={'push', 'pull'})


def build_buffer(i, ex, args, meta_args):
    """Store the input value and output saved value.

    In pull mode, the trigger is used to update the internal value.
    In push mode, the trigger is used to output the internal value.

    Can be used to cache changing values
    """
    args.start_value = hive.parameter(meta_args.data_type, None)
    ex.value = hive.attribute(meta_args.data_type, args.start_value)

    if meta_args.mode == "push":
        i.input = hive.push_in(ex.value)
        ex.input = hive.antenna(i.input)

        i.output = hive.push_out(ex.value)
        ex.output = hive.output(i.output)

        ex.trigger = hive.entry(i.output)

    elif meta_args.mode == "pull":
        i.input = hive.pull_in(ex.value)
        ex.input = hive.antenna(i.input)

        i.output = hive.pull_out(ex.value)
        ex.output = hive.output(i.output)

        ex.trigger = hive.entry(i.input)


Buffer = hive.dyna_hive("Buffer", build_buffer, declarator=declare_buffer)
