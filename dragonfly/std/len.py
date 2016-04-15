import hive


def do_len(self):
    self._length = len(self._object)


def build_len(i, ex, args, meta_args):
    """Determine length of object"""
    i.object = hive.attribute()
    i.pull_object = hive.pull_in(i.object)
    ex.object = hive.antenna(i.pull_object)

    i.length = hive.attribute('int')
    i.pull_length = hive.pull_out(i.length)
    ex.length = hive.output(i.pull_object)

    i.do_length = hive.modifier(do_len)

    hive.trigger(i.pull_length, i.pull_object, pretrigger=True)
    hive.trigger(i.pull_object, i.do_length)


Len = hive.hive("Len", build_len)
