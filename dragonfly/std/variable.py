import hive


def declare_variable(meta_args):
    meta_args.data_type = hive.parameter("tuple", ("int",))


def build_variable(i, ex, args, meta_args):
    """Simple value-holding hive"""
    args.start_value = hive.parameter(meta_args.data_type)
    ex.value = hive.attribute(meta_args.data_type, args.start_value)

    i.pull_value = hive.pull_out(ex.value)
    ex.value_out = hive.output(i.pull_value)

    i.push_value = hive.push_in(ex.value)
    ex.value_in = hive.antenna(i.push_value)


Variable = hive.dyna_hive("Variable", build_variable, declarator=declare_variable)
