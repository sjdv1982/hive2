import hive


def do_setattr(self):
    setattr(self._object_, self._name, self._value)


def declare_setattr(meta_args):
    meta_args.object_type = hive.parameter("str")
    meta_args.attribute_type = hive.parameter("str")


def build_setattr(i, ex, args, meta_args):
    """Set attribute on object"""
    i.name = hive.attribute("str")
    i.pull_name = hive.pull_in(i.name)

    i.value = hive.attribute(meta_args.attribute_type)
    i.push_value = hive.push_in(i.value)

    i.object_ = hive.attribute(meta_args.object_type)
    i.pull_object = hive.pull_in(i.object_)

    ex.object_ = hive.antenna(i.pull_object)
    ex.name = hive.antenna(i.pull_name)
    ex.value = hive.antenna(i.push_value)

    i.do_set_attr = hive.modifier(do_setattr)

    hive.trigger(i.push_value, i.pull_object)
    hive.trigger(i.pull_object, i.pull_name)
    hive.trigger(i.pull_name, i.do_set_attr)


SetAttr = hive.dyna_hive("SetAttr", build_setattr, declarator=declare_setattr)
