import hive

from ..std import Buffer


class DictCls:

    def __init__(self):
        self._dict = {}
        self._hive = hive.get_run_hive()

    def set_value(self):
        key = self._hive.key.value
        value = self._hive.value.value

        self._dict[key] = value

    def get_value(self):
        key = self._hive.key.value
        value = self._dict[key]
        self._hive.do_out()


def declare_dictionary(args):
    args.data_type = hive.parameter("str", "int")


def build_dictionary(cls, i, ex, args):
    i.key = Buffer(data_type="id")
    ex.key = hive.antenna(i.key.input)

    i.in_value = Buffer(data_type=args.data_type)
    ex.in_value = hive.antenna(i.in_value.input)

    i.out_value = hive.variable(args.data_type)
    i.out_io = hive.push_out(i.out_value)
    ex.out_value = hive.output(i.out_io)

    i.do_out = hive.triggerfunc()
    hive.trigger(i.do_out, i.out_io)

    i.get_value = hive.triggerable(cls.get_value)
    ex.get_value = hive.entry(i.get_value)

    i.set_value = hive.triggerable(cls.set_value)
    ex.set_value = hive.entry(i.set_value)


Dictionary = hive.hive("Dictionary", build_dictionary, DictCls, declarator=declare_dictionary)