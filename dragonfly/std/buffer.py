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
    i.cached_value = hive.attribute(meta_args.data_type, args.start_value)

    if meta_args.mode == "push":
        i.push_value = hive.push_in(i.cached_value)
        ex.value = hive.antenna(i.push_value)

        i.push_cached_value = hive.push_out(i.cached_value)
        ex.cached_value = hive.output(i.push_cached_value)

        ex.push = hive.entry(i.output)

    elif meta_args.mode == "pull":
        i.pull_value = hive.pull_in(i.cached_value)
        ex.value = hive.antenna(i.pull_value)

        i.pull_cached_value = hive.pull_out(i.cached_value)
        ex.cached_value = hive.output(i.pull_cached_value)

        ex.from_string = hive.entry(i.pull_value)


Buffer = hive.dyna_hive("Buffer", build_buffer, declarator=declare_buffer)
