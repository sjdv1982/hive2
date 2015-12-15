from operator import add, sub, mul, truediv, mod, eq, or_, not_, and_, gt, lt, ge, le

import hive


operators = {'+': add, '-': sub, '*': mul, '/': truediv, '%': mod, '=': eq, '!': not_, '|': or_, '&': and_,
             '>': gt, '<': lt, '>=': ge, '<=': le}

single_arg_operators = {not_,}

operator_names = set(operators)


def declare_operator(meta_args):
    meta_args.data_type = hive.parameter("tuple", ("int",))
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

    i.result = hive.attribute(meta_args.data_type)

    i.pull_a = hive.pull_in(i.a)
    ex.a = hive.antenna(i.pull_a)

    i.pull_result = hive.pull_out(i.result)
    ex.result = hive.output(i.pull_result)

    if is_single_arg:
        def calc(self):
            self._result = op(self._a)

    else:
        def calc(self):
            self._result = op(self._a, self._b)

        i.pull_b = hive.pull_in(i.b)
        ex.b = hive.antenna(i.pull_b)
        hive.trigger(i.pull_a, i.pull_b)

    i.run_operator = hive.modifier(calc)

    hive.trigger(i.pull_a, i.run_operator)
    hive.trigger(i.pull_result, i.pull_a, pretrigger=True)


Op = hive.dyna_hive("Op", build_operator, declare_operator)
