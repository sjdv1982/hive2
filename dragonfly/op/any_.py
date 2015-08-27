import hive
import string


def declare_any(args):
    args.count = hive.parameter("int", 1, options=set(range(26)))
    args.data_type = hive.parameter("str", "bool")


def build_any_func(count):
    argument_names = ["self._{}".format(char) for _, char in zip(range(count), string.ascii_lowercase)]
    argument_string = ', '.join(argument_names)

    func_body = """
def func(self):
    self._result = any({})
    """.format(argument_string)

    exec(func_body, locals(), globals())
    return func


def build_any(i, ex, args):
    # On pull
    func = build_any_func(args.count)
    i.trigger = hive.modifier(func)

    i.result = hive.attribute(args.data_type, False)
    pull_out = hive.pull_out(i.result)
    ex.output = hive.output(pull_out)

    hive.trigger(pull_out, i.trigger, pretrigger=True)

    for index, char in zip(range(args.count), string.ascii_lowercase):
        variable = hive.attribute(args.data_type, False)
        setattr(i, char, variable)

        pull_in = hive.pull_in(variable)

        antenna = hive.antenna(pull_in)
        setattr(ex, char, antenna)


Any = hive.hive("Any", build_any, declarator=declare_any)