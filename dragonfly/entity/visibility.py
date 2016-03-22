import hive


class VisibilityClass:

    def __init__(self):
        self._set_visibility = None
        self._get_visibility = None
        self._get_bound_entity = None

        self.entity = None
        self.parent = None

    def get_bound_entity(self):
        self.entity = self._get_bound_entity()

    def set_get_entity(self, get_entity):
        self._get_bound_entity = get_entity

    def set_set_visibility(self, set_visibility):
        self._set_visibility = set_visibility

    def set_get_visibility(self, get_visibility):
        self._get_visibility = get_visibility

    @hive.return_type('bool')
    def get_visibility(self):
        return self._get_visibility(self.entity)

    @hive.types(visible='bool')
    def set_visibility(self, visible):
        self._set_visibility(self.entity, visible)


def declare_visibility(meta_args):
    meta_args.mode = hive.parameter("str", "get", {'get', 'set'})
    meta_args.bound = hive.parameter("bool", True)


def build_visibility(cls, i, ex, args, meta_args):
    """Set/Get entity visibility"""

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier="entity.get_bound")
        i.do_get_entity = hive.triggerable(cls.get_bound_entity)

    else:
        i.entity = hive.property(cls, "entity", "entity")
        i.do_get_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.do_get_entity)

    if meta_args.mode == 'get':
        ex.get_get_visibility = hive.socket(cls.set_get_visibility, identifier="entity.visibility.get")
        i.pull_visibility = hive.pull_out(cls.get_visibility)
        ex.visibility = hive.output(i.pull_visibility)
        hive.trigger(i.pull_visibility, i.do_get_entity, pretrigger=True)

    else:
        ex.get_set_visibility = hive.socket(cls.set_set_visibility, identifier="entity.visibility.set")
        i.push_in_visibility = hive.push_in(cls.set_visibility)
        ex.visibility = hive.antenna(i.push_in_visibility)
        hive.trigger(i.push_in_visibility, i.do_get_entity, pretrigger=True)


Visibility = hive.dyna_hive("Visibility", build_visibility, declare_visibility, cls=VisibilityClass)
