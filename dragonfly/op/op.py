import hive

from operator import add, sub, mul, truediv, mod


operators = {'add': add, 'mul': mul, 'div': truediv, 'sub': sub, 'mod': mod,
             '+': add, '-': sub, '*': mul, '/': truediv, '%': mod}


def declare_operator(args):
    args.mode = hive.parameter("str", "push")
    args.data_type = hive.parameter("str", "int")
    args.default_value = hive.parameter("int", 0)
    args.operator = hive.parameter("str", "add")


def build_operator(i, ex, args):
    assert args.operator in operators

    ex.a_v = hive.attribute(args.data_type, args.default_value)
    ex.b_v = hive.attribute(args.data_type, args.default_value)
    ex.c_v = hive.attribute(args.data_type)

    op = operators[args.operator]

    if args.mode == "push":
        i.a_in = hive.push_in(ex.a_v)
        ex.a = hive.antenna(i.a_in)

        i.b_in = hive.push_in(ex.b_v)
        ex.b = hive.antenna(i.b_in)

        i.c_out = hive.push_out(ex.c_v)
        ex.c = hive.output(i.c_out)

        i.trig = hive.triggerfunc()
        hive.trigger(i.trig, i.c_out)

        def calc(h):
            h.c_v = op(h.a_v, h.b_v)
            h._trig()

        i.calc = hive.modifier(calc)
        hive.trigger(i.a_in, i.calc)
        hive.trigger(i.b_in, i.calc)

    elif args.mode == "pull":
        i.a_in = hive.pull_in(ex.a_v)
        ex.a = hive.antenna(i.a_in)

        i.b_in = hive.pull_in(ex.b_v)
        ex.b = hive.antenna(i.b_in)

        i.c_out = hive.pull_out(ex.c_v)
        ex.c = hive.output(i.c_out)

        def calc(h):
            h.c_v = op(h.a_v,  h.b_v)

        i.calc = hive.modifier(calc)
        hive.trigger(i.b_in, i.calc)
        hive.trigger(i.a_in, i.b_in)
        hive.trigger(i.c_out, i.a_in, pretrigger=True)

    else:
        raise ValueError("Invalid mode {}".format(args.mode))


Op = hive.hive("Op", build_operator, declarator=declare_operator)