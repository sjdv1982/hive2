import hive


class TransformClass:

    def __init__(self):
        self.position = None
        self.orientation = None
        self.entity = None

        self._get_orientation = None
        self._get_orientation = None
        self._get_entity = None

    def do_get_entity(self):
        self.entity = self._get_entity()

    def do_get_position(self):
        self.position = self._get_orientation(self.entity)

    def do_get_orientation(self):
        self.orientation = self._get_orientation(self.entity)

    def set_get_position(self, get_position):
        self._get_orientation = get_position

    def set_get_orientation(self, get_orientation):
        self._get_orientation = get_orientation

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_transform(meta_args):
    meta_args.coordinate_system = hive.parameter("str", 'absolute', options={'absolute', 'relative'})
    meta_args.bound = hive.parameter("bool", False)


def build_transform(cls, i, ex, args, meta_args):
    """Get transform attributes of an object"""
    coordinate_system = meta_args.coordinate_system

    i.position = hive.property(cls, "position", "vector")
    i.pull_position = hive.pull_out(i.position)
    ex.position = hive.output(i.pull_position)

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier=("entity", "get_bound"))
        i.do_get_entity = hive.triggerable(cls.do_get_entity)

    else:
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)

    i.orientation = hive.property(cls, "orientation", "vector")
    i.pull_orientation = hive.pull_out(i.orientation)
    ex.orientation = hive.output(i.pull_orientation)

    if coordinate_system == 'absolute':
        ex.get_get_position = hive.socket(cls.set_get_position, identifier=("entity", "position", "absolute", "get"))
        ex.get_get_orientation = hive.socket(cls.set_get_orientation, identifier=("entity", "orientation", "absolute",
                                                                                  "get"))

    else:
        ex.get_get_position = hive.socket(cls.set_get_position, identifier=("entity", "position", "relative", "get"))
        ex.get_get_orientation = hive.socket(cls.set_get_orientation, identifier=("entity", "orientation", "relative",
                                                                                  "get"))

    i.do_get_position = hive.triggerable(cls.do_get_position)
    i.do_get_orientation = hive.triggerable(cls.do_get_orientation)

    if meta_args.bound:
        hive.trigger(i.pull_orientation, i.do_get_entity, pretrigger=True)
        hive.trigger(i.pull_position, i.do_get_entity, pretrigger=True)

    else:
        hive.trigger(i.pull_orientation, i.pull_entity, pretrigger=True)
        hive.trigger(i.pull_position, i.pull_entity, pretrigger=True)

    hive.trigger(i.pull_orientation, i.do_get_orientation, pretrigger=True)
    hive.trigger(i.pull_position, i.do_get_position, pretrigger=True)


GetTransform = hive.dyna_hive("GetTransform", build_transform, declare_transform, cls=TransformClass)