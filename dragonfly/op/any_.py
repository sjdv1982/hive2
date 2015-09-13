import hive
import string


def declare_any(meta_args):
    meta_args.count = hive.parameter("int", 1, options=set(range(26)))
    meta_args.data_type = hive.parameter("str", "bool")


def build_any_func(count):
    argument_names = ["self._{}".format(char) for _, char in zip(range(count), string.ascii_lowercase)]
    argument_string = ', '.join(argument_names)

    func_body = """
def func(self):
    self._result = any({})
    """.format(argument_string)

    exec(func_body, locals(), globals())
    return func


def build_any(i, ex, args, meta_args):
    """Trigger output if any inputs evaluate to True"""
    # On pull
    func = build_any_func(meta_args.count)
    i.trigger = hive.modifier(func)

    i.result = hive.attribute(meta_args.data_type, False)
    pull_out = hive.pull_out(i.result)
    ex.output = hive.output(pull_out)

    hive.trigger(pull_out, i.trigger, pretrigger=True)

    for index, char in zip(range(meta_args.count), string.ascii_lowercase):
        variable = hive.attribute(meta_args.data_type, False)
        setattr(i, char, variable)

        pull_in = hive.pull_in(variable)

        antenna = hive.antenna(pull_in)
        setattr(ex, char, antenna)


Any = hive.dyna_hive("Any", build_any, declare_any)