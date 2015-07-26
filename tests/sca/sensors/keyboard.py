import hive


def build_keyboard(i, ex, args):
    def poll(h):
        result = input("Enter a key for {}".format(h.name))
        h.is_positive = result == h.key
        h.trig_out()

    ex.name = hive.attribute(("str",), "<Sensor>")
    ex.key = hive.attribute(("str",), "w")
    ex.is_positive = hive.attribute(("bool",), False)

    i.positive = hive.pull_out(ex.is_positive)
    ex.positive = hive.output(i.positive)

    i.trig_in = hive.modifier(poll)
    ex.trig_in = hive.entry(i.trig_in)

    i.trig_out = hive.triggerfunc()
    ex.trig_out = hive.hook(i.trig_out)


Keyboard = hive.hive("Keyboard", build_keyboard)