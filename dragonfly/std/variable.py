import hive


def declare_variable(args):
    args.data_type = hive.parameter("str", "int")
    args.start_value = hive.parameter("int", 0)


def build_variable(i, ex, args):
    i.value = hive.variable(args.data_type, args.start_value)
    value_out = hive.pull_out(i.value)
    ex.value = hive.output(value_out)


Variable = hive.hive("Variable", build_variable, declarator=declare_variable)