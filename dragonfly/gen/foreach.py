import hive


primitive_non_iterable = {'int', 'float', 'bool'}


def declare_foreach(meta_args):
    meta_args.data_type = hive.parameter("tuple", ("int",))


def do_iter(self):
    for item in self._iterable:
        self._value = item
        self.value_out.push()


def build_foreach(i, ex, args, meta_args):
    """Iterate over iterable object"""
    # Set iterable
    i.iterable = hive.attribute()
    i.pull_iterable = hive.pull_in(i.iterable)
    ex.iterable = hive.antenna(i.pull_iterable)

    i.do_trig = hive.triggerfunc()
    i.trig_in = hive.triggerable(i.do_trig)
    ex.trig_in = hive.entry(i.trig_in)

    i.value = hive.attribute(meta_args.data_type)
    i.value_out = hive.push_out(i.value)
    ex.value_out = hive.output(i.value_out)

    i.iter = hive.modifier(do_iter)
    hive.trigger(i.do_trig, i.pull_iterable)
    hive.trigger(i.do_trig, i.iter)


ForEach = hive.dyna_hive("ForEach", build_foreach, declare_foreach)
