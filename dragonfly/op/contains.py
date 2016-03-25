import hive


def declare_contains(meta_args):
    meta_args.container_type = hive.parameter('str')
    meta_args.item_type = hive.parameter('str', 'str')


def build_contains(i, ex, args, meta_args):
    """Interface to Python contains operator"""
    def contains(self):
        self._result = self._item in self._container

    i.do_contains = hive.modifier(contains)

    i.container = hive.attribute(meta_args.container_type)
    i.pull_container = hive.pull_in(i.container)
    ex.container = hive.antenna(i.pull_container)

    i.item = hive.attribute(meta_args.item_type)
    i.pull_item = hive.pull_in(i.item)
    ex.item = hive.antenna(i.pull_item)

    i.result = hive.attribute('bool')
    i.pull_result = hive.pull_out(i.result)
    ex.result = hive.output(i.pull_result)

    hive.trigger(i.pull_result, i.pull_container, pretrigger=True)
    hive.trigger(i.pull_container, i.pull_item)
    hive.trigger(i.pull_item, i.do_contains)


Contains = hive.dyna_hive("Contains", build_contains, declare_contains)
