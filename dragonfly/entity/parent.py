import hive


class ParentClass:

    def __init__(self):
        self._set_parent = None
        self._get_parent = None
        self._get_entity = None

        self.entity = None
        self.parent = None

    def set_parent(self):
        self._set_parent(self.entity, self.parent)

    def get_parent(self):
        self.parent = self._get_parent(self.entity)

    def get_entity(self):
        self.entity = self._get_entity()

    def set_set_parent(self, set_parent):
        self._set_parent = set_parent

    def set_get_parent(self, get_parent):
        self._get_parent = get_parent

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_parent(meta_args):
    meta_args.mode = hive.parameter("str", "get", {'get', 'set'})
    meta_args.bound = hive.parameter("bool", True)


def build_parent(cls, i, ex, args, meta_args):
    """Set/Get entity parent"""
    ex.get_get_parent = hive.socket(cls.set_get_parent, identifier="entity.parent.get")
    ex.get_set_parent = hive.socket(cls.set_set_parent, identifier="entity.parent.set")

    i.parent_ = hive.property(cls, "parent", "entity")

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier="entity.get_bound")
        i.do_get_entity = hive.triggerable(cls.get_entity)

    else:
        i.entity = hive.property(cls, "entity", "entity")
        i.do_get_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.do_get_entity)

    if meta_args.mode == "get":
        i.pull_parent = hive.pull_out(i.parent_)
        ex.parent_ = hive.output(i.pull_parent)

        i.get_parent = hive.triggerable(cls.get_parent)
        hive.trigger(i.pull_parent, i.do_get_entity, pretrigger=True)
        hive.trigger(i.pull_parent, i.get_parent, pretrigger=True)

    else:
        i.push_parent = hive.push_in(i.parent_)
        ex.parent_ = hive.antenna(i.push_parent)

        i.set_parent = hive.triggerable(cls.set_parent)
        hive.trigger(i.push_parent, i.do_get_entity)
        hive.trigger(i.push_parent, i.set_parent)


Parent = hive.dyna_hive("Parent", build_parent, declare_parent, cls=ParentClass)
