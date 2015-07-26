from __future__ import print_function


import hive


def build_nand(i, ex, args):
    ex.a = hive.attribute("bool", False)
    ex.b = hive.attribute("bool", False)

    def on_nand(h):
        if not (h.a and h.b):
            h.trig_out()

    i.trig_out = hive.triggerfunc()
    i.trig_in = hive.modifier(on_nand)

    ex.trig_out = hive.hook(i.trig_out)
    ex.trig_in = hive.entry(i.trig_in)


NAND = hive.hive("NAND", build_nand)