from operator import add, sub, mul, truediv, mod, eq, or_, not_, and_, gt, lt, ge, le

import hive


operators = {'+': add, '-': sub, '*': mul, '/': truediv, '%': mod, '=': eq, '!': not_, '|': or_, '&': and_,
             '>': gt, '<': lt, '>=': ge, '<=': le}

single_arg_operators = {not_,}

operator_names = set(operators)


def declare_operator(meta_args):
    meta_args.data_type = hive.parameter("str", ("int",))
    meta_args.operator = hive.parameter("str", "+", options=operator_names)


def build_operator(i, ex, args, meta_args):
    """HIVE interface to python "operator" module"""
    assert meta_args.operator in operators
    args.default_value = hive.parameter("int", 0)

    op = operators[meta_args.operator]
    is_single_arg = op in single_arg_operators

    i.a = hive.attribute(meta_args.data_type, args.default_value)

    if not is_single_arg:
        i.b = hive.attribute(meta_args.data_type, args.default_value)

    i.c = hive.attribute(meta_args.data_type)

    i.a_in = hive.pull_in(i.a)
    ex.a = hive.antenna(i.a_in)

    i.c_out = hive.pull_out(i.c)
    ex.c = hive.output(i.c_out)

    if is_single_arg:
        def calc(self):
            self._c = op(self._a)

    else:
        def calc(self):
            self._c = op(self._a, self._b)

        i.b_in = hive.pull_in(i.b)
        ex.b = hive.antenna(i.b_in)
        hive.trigger(i.a_in, i.b_in)

    i.calc = hive.modifier(calc)

    hive.trigger(i.a_in, i.calc)
    hive.trigger(i.c_out, i.a_in, pretrigger=True)


Op = hive.dyna_hive("Op", build_operator, declare_operator)