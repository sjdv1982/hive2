import hive


def declare_list(meta_args):
    meta_args.data_type = hive.parameter('str', 'int')


def build_list(i, ex, args, meta_args):
    """Perform list operation on single lists"""

    i.list_ = hive.attribute('list', list())
    i.pull_list_ = hive.pull_out(i.list_)
    ex.list_out = hive.output(i.pull_list_)

    i.push_list_ = hive.push_in(i.list_)
    ex.list_ = hive.antenna(i.push_list_)

    # Pop item
    i.popped_item = hive.attribute(meta_args.data_type)
    i.pull_pop = hive.pull_out(i.popped_item)
    ex.pop = hive.output(i.pull_pop)

    def do_pop(self):
        self._popped_item = self._list_.pop()

    i.do_pop = hive.modifier(do_pop)
    hive.trigger(i.pull_pop, i.do_pop, pretrigger=True)

    # Add item
    i.to_append = hive.attribute(meta_args.data_type)
    i.push_to_append = hive.push_in(i.to_append)
    ex.append = hive.antenna(i.push_to_append)

    def to_append(self):
        self._list_.append(self._to_append)

    i.do_append = hive.modifier(to_append)
    hive.trigger(i.push_to_append, i.do_append)

    # Remove item
    i.to_remove = hive.attribute(meta_args.data_type)
    i.push_to_remove = hive.push_in(i.to_remove)
    ex.remove = hive.antenna(i.push_to_remove)

    def do_remove(self):
        self._list_.remove(self._to_remove)

    i.do_remove = hive.modifier(do_remove)
    hive.trigger(i.push_to_remove, i.do_remove)

    def do_clear(self):
        self._list_.clear()

    i.do_clear = hive.modifier(do_clear)
    ex.clear = hive.entry(i.do_clear)


List = hive.dyna_hive("List", build_list, declare_list)
