import hive


def do_getattr(self):
    self._value = getattr(self._object_, self._name)


def declare_getattr(meta_args):
    meta_args.object_type = hive.parameter("str")
    meta_args.attribute_type = hive.parameter("str")


def build_getattr(i, ex, args, meta_args):
    """Get attribute from object"""
    i.name = hive.attribute("str")
    i.pull_name = hive.pull_in(i.name)

    i.value = hive.attribute(meta_args.attribute_type)
    i.pull_value = hive.pull_out(i.value)

    i.object_ = hive.attribute(meta_args.object_type)
    i.pull_object = hive.pull_in(i.object_)

    ex.object_ = hive.antenna(i.pull_object)
    ex.name = hive.antenna(i.pull_name)
    ex.value = hive.output(i.pull_value)

    i.do_get_attr = hive.modifier(do_getattr)

    hive.trigger(i.pull_value, i.pull_object, pretrigger=True)
    hive.trigger(i.pull_object, i.pull_name)
    hive.trigger(i.pull_name, i.do_get_attr)


GetAttr = hive.dyna_hive("GetAttr", build_getattr, declarator=declare_getattr)
