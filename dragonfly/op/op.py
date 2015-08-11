import hive

from operator import add, sub, mul, truediv, mod, eq, or_, not_, and_


operators = {'add': add, 'mul': mul, 'div': truediv, 'sub': sub, 'mod': mod, 'eq': eq, 'not': not_, 'or': or_,
             'and': and_, '+': add, '-': sub, '*': mul, '/': truediv, '%': mod, '=': eq, '!': not_, '|': or_, '&': and_}

single_arg_operators = {not_,}

operator_names = set(operators)


def declare_operator(args):
    args.mode = hive.parameter("str", "push", options={"push", "pull"})
    args.data_type = hive.parameter("str", "int")
    args.default_value = hive.parameter("int", 0)
    args.operator = hive.parameter("str", "add", options=operator_names)


def build_operator(i, ex, args):
    assert args.operator in operators

    op = operators[args.operator]
    is_single_arg = op in single_arg_operators

    i.a = hive.variable(args.data_type, args.default_value)

    if not is_single_arg:
        i.b = hive.variable(args.data_type, args.default_value)

    i.c = hive.variable(args.data_type)

    if args.mode == "push":
        i.a_in = hive.push_in(i.a)
        ex.a = hive.antenna(i.a_in)

        i.c_out = hive.push_out(i.c)
        ex.c = hive.output(i.c_out)

        i.trig = hive.triggerfunc()

        # Trigger output when updated
        hive.trigger(i.a_in, i.c_out)

        # Single arg operators
        if is_single_arg:
            def calc(h):
                h._c = op(h._a)
                h._trig()

        else:
            i.b_in = hive.push_in(i.b)
            ex.b = hive.antenna(i.b_in)

            # Trigger output when updated
            hive.trigger(i.b_in, i.c_out)

            def calc(h):
                h._c = op(h._a, h._b)
                h._trig()

        # Trigger calculation before output
        i.calc = hive.modifier(calc)
        hive.trigger(i.c_out, i.calc, pretrigger=True)

    elif args.mode == "pull":
        i.a_in = hive.pull_in(i.a)
        ex.a = hive.antenna(i.a_in)

        i.c_out = hive.pull_out(i.c)
        ex.c = hive.output(i.c_out)

        if is_single_arg:
            def calc(h):
                h._c = op(h._a)

        else:
            def calc(h):
                h._c = op(h._a, h._b)

            i.b_in = hive.pull_in(i.b)
            ex.b = hive.antenna(i.b_in)
            hive.trigger(i.a_in, i.b_in)

        i.calc = hive.modifier(calc)

        hive.trigger(i.a_in, i.calc)
        hive.trigger(i.c_out, i.a_in, pretrigger=True)

    else:
        raise ValueError("Invalid mode {}".format(args.mode))


Op = hive.hive("Op", build_operator, declarator=declare_operator)