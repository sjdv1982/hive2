import hive


def declare_transistor(args):
    args.data_type = hive.parameter("str", "int")


def build_transistor(i, ex, args):
    i.in_value = hive.variable(args.data_type)
    i.input = hive.pull_in(i.in_value)
    ex.input = hive.antenna(i.input)

    i.output = hive.push_out(i.in_value)
    ex.output = hive.output(i.output)

    i.trigger = hive.triggerfunc()

    def on_triggered(h):
        h.input.pull()
        h.output.push()

    i.modifier = hive.modifier(on_triggered)
    ex.trigger = hive.entry(i.modifier)


Transistor = hive.hive("Transistor", build_transistor, declarator=declare_transistor)