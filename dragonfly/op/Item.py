import hive


def do_setitem(self):
    self._object_[self._name] = self._value


def do_getitem(self):
    self._value = self._object_[self._name]


def declare_item(meta_args):
    meta_args.mode = hive.parameter("str", "get", options={"get", "set"})
    meta_args.object_type = hive.parameter("str")
    meta_args.item_type = hive.parameter("str")


def build_item(i, ex, args, meta_args):
    """Set/get item in object"""
    i.name = hive.attribute("str")
    i.value = hive.attribute(meta_args.item_type)
    i.object_ = hive.attribute(meta_args.object_type)

    i.pull_name = hive.pull_in(i.name)
    i.pull_object = hive.pull_in(i.object_)

    ex.object_ = hive.antenna(i.pull_object)
    ex.name = hive.antenna(i.pull_name)

    if meta_args.mode == "set":
        i.push_value = hive.push_in(i.value)
        ex.value = hive.antenna(i.push_value)

        i.do_set_attr = hive.modifier(do_setitem)

        hive.trigger(i.push_value, i.pull_object)
        hive.trigger(i.pull_object, i.pull_name)
        hive.trigger(i.pull_name, i.do_set_attr)

    else:
        i.pull_value = hive.pull_out(i.value)
        ex.value = hive.output(i.pull_value)

        i.do_get_attr = hive.modifier(do_getitem)

        hive.trigger(i.pull_value, i.pull_object, pretrigger=True)
        hive.trigger(i.pull_object, i.pull_name)
        hive.trigger(i.pull_name, i.do_get_attr)


Item = hive.dyna_hive("Item", build_item, declarator=declare_item)
