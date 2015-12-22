import hive


class TransformClass:

    def __init__(self):
        self.position = None
        self.orientation = None
        self.entity = None

        self._set_position = None
        self._set_orientation = None

        self._get_entity = None

    def do_get_entity(self):
        self.entity = self._get_entity()

    def do_set_position(self):
        self._set_position(self.entity, self.position)

    def do_set_orientation(self):
        self._set_orientation(self.entity, self.orientation)

    def set_set_position(self, set_position):
        self._set_position = set_position

    def set_set_orientation(self, set_orientation):
        self._set_orientation = set_orientation

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_transform(meta_args):
    meta_args.coordinate_system = hive.parameter("str", 'absolute', options={'absolute', 'relative'})
    meta_args.bound = hive.parameter("bool", False)


def build_transform(cls, i, ex, args, meta_args):
    """Set transform attributes of an object"""
    coordinate_system = meta_args.coordinate_system

    i.position = hive.property(cls, "position", "vector")
    i.push_position = hive.push_in(i.position)
    ex.position = hive.antenna(i.push_position)

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier=("entity", "get_bound"))
        i.do_get_entity = hive.triggerable(cls.do_get_entity)

    else:
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)

    i.orientation = hive.property(cls, "orientation", "vector")
    i.push_orientation = hive.push_in(i.orientation)
    ex.orientation = hive.antenna(i.push_orientation)

    if coordinate_system == 'absolute':
        ex.get_set_position = hive.socket(cls.set_set_position, identifier=("entity", "position", "absolute", "set"))
        ex.get_set_orientation = hive.socket(cls.set_set_orientation, identifier=("entity", "orientation", "absolute",
                                                                                  "set"))

    else:
        ex.get_set_position = hive.socket(cls.set_set_position, identifier=("entity", "position", "relative", "set"))
        ex.get_set_orientation = hive.socket(cls.set_set_orientation, identifier=("entity", "orientation", "relative",
                                                                                  "set"))

    i.do_set_position = hive.triggerable(cls.do_set_position)
    i.do_set_orientation = hive.triggerable(cls.do_set_orientation)

    if meta_args.bound:
        hive.trigger(i.push_position, i.do_get_entity)
        hive.trigger(i.push_orientation, i.do_get_entity)

    else:
        hive.trigger(i.push_orientation, i.pull_entity)
        hive.trigger(i.push_position, i.pull_entity)

    hive.trigger(i.push_orientation, i.do_set_orientation)
    hive.trigger(i.push_position, i.do_set_position)


SetTransform = hive.dyna_hive("SetTransform", build_transform, declare_transform, cls=TransformClass)