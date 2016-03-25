import hive


class AngularClass:

    def __init__(self):
        self.angular = None

        self.entity = None
        self.other_entity = None

        self._get_angular = None
        self._get_entity = None

        self._set_angular = None
        self._set_entity = None

    def do_get_entity(self):
        self.entity = self._get_entity()

    def do_get_angular(self):
        self.angular = self._get_angular(self.entity)

    def do_get_relative_angular(self):
        self.angular = self._get_angular(self.entity, self.other_entity)

    def do_set_angular(self):
        self._set_angular(self.entity, self.angular)

    def do_set_relative_angular(self):
        self._set_angular(self.entity, self.other_entity, self.angular)

    def set_get_angular(self, get_angular):
        self._get_angular = get_angular

    def set_set_angular(self, set_angular):
        self._set_angular = set_angular

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_angular(meta_args):
    meta_args.bound = hive.parameter("bool", True)
    meta_args.coordinate_system = hive.parameter("str", 'absolute', options={'absolute', 'relative'})
    meta_args.mode = hive.parameter("str", "get", options={"get", "set"})


def build_angular(cls, i, ex, args, meta_args):
    """Access to entity angular API"""
    coordinate_system = meta_args.coordinate_system

    i.angular = hive.property(cls, "angular", "vector")

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier="entity.get_bound")
        i.do_get_entity = hive.triggerable(cls.do_get_entity)

    else:
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)

    if coordinate_system == 'relative':
        i.other_entity = hive.property(cls, "other_entity", "entity")
        i.pull_other_entity = hive.pull_in(i.other_entity)
        ex.other_entity = hive.antenna(i.pull_other_entity)

    if meta_args.mode == "get":
        i.pull_angular = hive.pull_out(i.angular)
        ex.angular = hive.output(i.pull_angular)

    else:
        i.push_angular = hive.push_in(i.angular)
        ex.angular = hive.antenna(i.push_angular)

    if meta_args.mode == "get":
        if coordinate_system == 'absolute':
            ex.get_get_angular = hive.socket(cls.set_get_angular, identifier="entity.angular.get.absolute")
            i.do_get_angular = hive.triggerable(cls.do_get_angular)

        else:
            ex.get_get_angular = hive.socket(cls.set_get_angular, identifier="entity.angular.get.relative")
            i.do_get_angular = hive.triggerable(cls.do_get_relative_angular)
            hive.trigger(i.pull_angular, i.pull_other_entity, pretrigger=True)

        if meta_args.bound:
            hive.trigger(i.pull_angular, i.do_get_entity, pretrigger=True)

        else:
            hive.trigger(i.pull_angular, i.pull_entity, pretrigger=True)

        hive.trigger(i.pull_angular, i.do_get_angular, pretrigger=True)

    else:
        if coordinate_system == 'absolute':
            ex.get_set_angular = hive.socket(cls.set_set_angular, identifier="entity.angular.set.absolute")
            i.do_set_angular = hive.triggerable(cls.do_set_angular)

        else:
            ex.get_set_angular = hive.socket(cls.set_set_angular, identifier="entity.angular.set.relative")
            i.do_set_angular = hive.triggerable(cls.do_set_relative_angular)
            hive.trigger(i.push_angular, i.pull_other_entity)

        if meta_args.bound:
            hive.trigger(i.push_angular, i.do_get_entity)

        else:
            hive.trigger(i.push_angular, i.pull_entity)

        hive.trigger(i.push_angular, i.do_set_angular)


Angular = hive.dyna_hive("Angular", build_angular, declare_angular, builder_cls=AngularClass)
