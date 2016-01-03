import hive


class OrientationClass:

    def __init__(self):
        self.orientation = None

        self.entity = None
        self.other_entity = None

        self._get_orientation = None
        self._get_entity = None

        self._set_orientation = None
        self._set_entity = None

    def do_get_entity(self):
        self.entity = self._get_entity()

    def do_get_orientation(self):
        self.orientation = self._get_orientation(self.entity)

    def do_get_relative_orientation(self):
        self.orientation = self._get_orientation(self.entity, self.other_entity)

    def do_set_orientation(self):
        self._set_orientation(self.entity, self.orientation)

    def do_set_relative_orientation(self):
        self._set_orientation(self.entity, self.other_entity, self.orientation)

    def set_get_orientation(self, get_orientation):
        self._get_orientation = get_orientation

    def set_set_orientation(self, set_orientation):
        self._set_orientation = set_orientation

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_orientation(meta_args):
    meta_args.bound = hive.parameter("bool", True)
    meta_args.coordinate_system = hive.parameter("str", 'absolute', options={'absolute', 'relative'})
    meta_args.mode = hive.parameter("str", "get", options={"get", "set"})


def build_orientation(cls, i, ex, args, meta_args):
    """Access to entity orientation API"""
    coordinate_system = meta_args.coordinate_system

    i.orientation = hive.property(cls, "orientation", "euler")

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
        i.pull_orientation = hive.pull_out(i.orientation)
        ex.orientation = hive.output(i.pull_orientation)

    else:
        i.pull_orientation = hive.pull_in(i.orientation)
        ex.orientation = hive.antenna(i.pull_orientation)

        ex.trig = hive.entry(i.pull_orientation)

    if meta_args.mode == "get":
        if coordinate_system == 'absolute':
            ex.get_get_orientation = hive.socket(cls.set_get_orientation, identifier="entity.orientation.get.absolute")

            i.do_get_orientation = hive.triggerable(cls.do_get_orientation)

        else:
            ex.get_get_orientation = hive.socket(cls.set_get_orientation, identifier="entity.orientation.get.relative")
            i.do_get_orientation = hive.triggerable(cls.do_get_relative_orientation)
            hive.trigger(i.pull_orientation, i.pull_other_entity, pretrigger=True)

        if meta_args.bound:
            hive.trigger(i.pull_orientation, i.do_get_entity, pretrigger=True)

        else:
            hive.trigger(i.pull_orientation, i.pull_entity, pretrigger=True)

        hive.trigger(i.pull_orientation, i.do_get_orientation, pretrigger=True)

    else:
        if coordinate_system == 'absolute':
            ex.get_set_orientation = hive.socket(cls.set_set_orientation, identifier="entity.orientation.set.absolute")
            i.do_set_orientation = hive.triggerable(cls.do_set_orientation)

        else:
            ex.get_set_orientation = hive.socket(cls.set_set_orientation, identifier="entity.orientation.set.relative")
            i.do_set_orientation = hive.triggerable(cls.do_set_relative_orientation)
            hive.trigger(i.pull_orientation, i.pull_other_entity)

        if meta_args.bound:
            hive.trigger(i.pull_orientation, i.do_get_entity)

        else:
            hive.trigger(i.pull_orientation, i.pull_entity)

        hive.trigger(i.pull_orientation, i.do_set_orientation)


Orientation = hive.dyna_hive("Orientation", build_orientation, declare_orientation, cls=OrientationClass)