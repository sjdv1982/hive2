import hive


def declare_variable(args):
    args.data_type = hive.parameter("str", "int")


def build_variable(i, ex, args, meta_args):
    args.start_value = hive.parameter(meta_args.data_type)
    i.value = hive.attribute(meta_args.data_type, args.start_value)

    value_out = hive.pull_out(i.value)
    ex.value = hive.output(value_out)


Variable = hive.dyna_hive("Variable", build_variable, declarator=declare_variable)