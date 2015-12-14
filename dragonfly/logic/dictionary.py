import hive


class DictCls:

    def __init__(self):
        self.dict = None
        self.key = None
        self.value = None
        self._hive = hive.get_run_hive()

    def set_value(self):
        self.dict[self.key] = self.value

    def get_value(self):
        self.value = self.dict[self.key]


def declare_dictionary(meta_args):
    meta_args.data_type = hive.parameter("str", ("int",))
    meta_args.mode = hive.parameter("str", "get", {"get", "set"})


def build_dictionary(cls, i, ex, args, meta_args):
    """HIVE interface to dictionary object"""
    ex.dict = hive.property(cls, "dict", "dict")

    i.dict_in = hive.pull_in(ex.dict)
    ex.dict_in = hive.antenna(i.dict_in)

    ex.key = hive.property(cls, "key", ("str", "id"))
    i.key_in = hive.pull_in(ex.key)
    ex.key_in = hive.antenna(i.key_in)

    i.value = hive.property(cls, "value", meta_args.data_type)

    if meta_args.mode == "set":
        i.in_value = hive.push_in(i.value)
        ex.in_value = hive.antenna(i.in_value)

        i.set_value = hive.triggerable(cls.set_value)

        hive.trigger(i.in_value, i.key_in)
        hive.trigger(i.key_in, i.dict_in)
        hive.trigger(i.dict_in, i.set_value)

    elif meta_args.mode == "get":
        i.out_value = hive.pull_out(i.value)
        ex.out_value = hive.output(i.out_value)

        i.get_value = hive.triggerable(cls.get_value)

        # Before outputting, update key
        hive.trigger(i.out_value, i.key_in, pretrigger=True)
        hive.trigger(i.key_in, i.dict_in)
        hive.trigger(i.dict_in, i.get_value)


Dictionary = hive.dyna_hive("Dictionary", build_dictionary, declare_dictionary, DictCls)