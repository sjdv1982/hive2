import hive
import string


def declare_all(args):
    args.count = hive.parameter("int", 1, options=set(range(26)))
    args.data_type = hive.parameter("str", "bool")


def build_all_func(count):
    argument_names = ["self._{}".format(char) for _, char in zip(range(count), string.ascii_lowercase)]
    argument_string = ', '.join(argument_names)

    func_body = """
def func(self):
    self._result = all({})
    """.format(argument_string)

    exec(func_body, locals(), globals())
    return func


def build_all(i, ex, args):
    # On pull
    func = build_all_func(args.count)
    i.trigger = hive.modifier(func)

    i.result = hive.variable(args.data_type, False)
    pull_out = hive.pull_out(i.result)
    ex.output = hive.output(pull_out)

    hive.trigger(pull_out, i.trigger, pretrigger=True)

    for index, char in zip(range(args.count), string.ascii_lowercase):
        variable = hive.variable(args.data_type, False)
        setattr(i, char, variable)

        pull_in = hive.pull_in(variable)

        antenna = hive.antenna(pull_in)
        setattr(ex, char, antenna)


All = hive.hive("All", build_all, declarator=declare_all)