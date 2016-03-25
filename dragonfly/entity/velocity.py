import hive


class VelocityClass:

    def __init__(self):
        self.velocity = None

        self.entity = None
        self.other_entity = None

        self._get_velocity = None
        self._get_entity = None

        self._set_velocity = None
        self._set_entity = None

    def do_get_entity(self):
        self.entity = self._get_entity()

    def do_get_velocity(self):
        self.velocity = self._get_velocity(self.entity)

    def do_get_relative_velocity(self):
        self.velocity = self._get_velocity(self.entity, self.other_entity)

    def do_set_velocity(self):
        self._set_velocity(self.entity, self.velocity)

    def do_set_relative_velocity(self):
        self._set_velocity(self.entity, self.other_entity, self.velocity)

    def set_get_velocity(self, get_velocity):
        self._get_velocity = get_velocity

    def set_set_velocity(self, set_velocity):
        self._set_velocity = set_velocity

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_velocity(meta_args):
    meta_args.bound = hive.parameter("bool", True)
    meta_args.coordinate_system = hive.parameter("str", 'absolute', options={'absolute', 'relative'})
    meta_args.mode = hive.parameter("str", "get", options={"get", "set"})


def build_velocity(cls, i, ex, args, meta_args):
    """Access to entity velocity API"""
    coordinate_system = meta_args.coordinate_system

    i.velocity = hive.property(cls, "velocity", "vector")

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
        i.pull_velocity = hive.pull_out(i.velocity)
        ex.velocity = hive.output(i.pull_velocity)

    else:
        i.push_velocity = hive.push_in(i.velocity)
        ex.velocity = hive.antenna(i.push_velocity)

    if meta_args.mode == "get":
        if coordinate_system == 'absolute':
            ex.get_get_velocity = hive.socket(cls.set_get_velocity, identifier="entity.velocity.get.absolute")
            i.do_get_velocity = hive.triggerable(cls.do_get_velocity)

        else:
            ex.get_get_velocity = hive.socket(cls.set_get_velocity, identifier="entity.velocity.get.relative")
            i.do_get_velocity = hive.triggerable(cls.do_get_relative_velocity)
            hive.trigger(i.pull_velocity, i.pull_other_entity, pretrigger=True)

        if meta_args.bound:
            hive.trigger(i.pull_velocity, i.do_get_entity, pretrigger=True)

        else:
            hive.trigger(i.pull_velocity, i.pull_entity, pretrigger=True)

        hive.trigger(i.pull_velocity, i.do_get_velocity, pretrigger=True)

    else:
        if coordinate_system == 'absolute':
            ex.get_set_velocity = hive.socket(cls.set_set_velocity, identifier="entity.velocity.set.absolute")
            i.do_set_velocity = hive.triggerable(cls.do_set_velocity)

        else:
            ex.get_set_velocity = hive.socket(cls.set_set_velocity, identifier="entity.velocity.set.relative")
            i.do_set_velocity = hive.triggerable(cls.do_set_relative_velocity)
            hive.trigger(i.push_velocity, i.pull_other_entity)

        if meta_args.bound:
            hive.trigger(i.push_velocity, i.do_get_entity)

        else:
            hive.trigger(i.push_velocity, i.pull_entity)

        hive.trigger(i.push_velocity, i.do_set_velocity)


Velocity = hive.dyna_hive("Velocity", build_velocity, declare_velocity, builder_cls=VelocityClass)
