import hive


def build_print(i, ex, args):
    """Print value to system console"""
    ex.value = hive.attribute()
    i.value_in = hive.push_in(ex.value)
    ex.value_in = hive.antenna(i.value_in)

    i.func = hive.modifier(lambda self: print(self.value))

    hive.trigger(i.value_in, i.func)


Print = hive.hive("Print", build_print)