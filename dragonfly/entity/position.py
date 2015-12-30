import hive


class PositionClass:

    def __init__(self):
        self.position = None

        self.entity = None
        self.other_entity = None

        self._get_position = None
        self._get_entity = None

        self._set_position = None
        self._set_entity = None

    def do_get_entity(self):
        self.entity = self._get_entity()

    def do_get_position(self):
        self.position = self._get_position(self.entity)

    def do_get_relative_position(self):
        self.position = self._get_position(self.entity, self.other_entity)

    def do_set_position(self):
        self._set_position(self.entity, self.position)

    def do_set_relative_position(self):
        self._set_position(self.entity, self.other_entity, self.position)

    def set_get_position(self, get_position):
        self._get_position = get_position

    def set_set_position(self, set_position):
        self._set_position = set_position

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_position(meta_args):
    meta_args.bound = hive.parameter("bool", True)
    meta_args.coordinate_system = hive.parameter("str", 'absolute', options={'absolute', 'relative'})
    meta_args.mode = hive.parameter("str", "get", options={"get", "set"})


def build_position(cls, i, ex, args, meta_args):
    """Access to entity position API"""
    coordinate_system = meta_args.coordinate_system

    i.position = hive.property(cls, "position", "vector")

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier=("entity", "get_bound"))
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
        i.pull_position = hive.pull_out(i.position)
        ex.position = hive.output(i.pull_position)

    else:
        i.pull_position = hive.pull_in(i.position)
        ex.position = hive.antenna(i.pull_position)

        ex.trig = hive.entry(i.pull_position)

    if meta_args.mode == "get":
        if coordinate_system == 'absolute':
            ex.get_get_position = hive.socket(cls.set_get_position, identifier=("entity", "position", "get",
                                                                                "absolute"))

            i.do_get_position = hive.triggerable(cls.do_get_position)

        else:
            ex.get_get_position = hive.socket(cls.set_get_position, identifier=("entity", "position", "get",
                                                                                "relative"))
            i.do_get_position = hive.triggerable(cls.do_get_relative_position)
            hive.trigger(i.pull_position, i.pull_other_entity, pretrigger=True)

        if meta_args.bound:
            hive.trigger(i.pull_position, i.do_get_entity, pretrigger=True)

        else:
            hive.trigger(i.pull_position, i.pull_entity, pretrigger=True)

        hive.trigger(i.pull_position, i.do_get_position, pretrigger=True)

    else:
        if coordinate_system == 'absolute':
            ex.get_set_position = hive.socket(cls.set_set_position, identifier=("entity", "position", "set",
                                                                                "absolute"))
            i.do_set_position = hive.triggerable(cls.do_set_position)

        else:
            ex.get_set_position = hive.socket(cls.set_set_position, identifier=("entity", "position", "set",
                                                                                "relative"))
            i.do_set_position = hive.triggerable(cls.do_set_relative_position)
            hive.trigger(i.pull_position, i.pull_other_entity)

        if meta_args.bound:
            hive.trigger(i.pull_position, i.do_get_entity)

        else:
            hive.trigger(i.pull_position, i.pull_entity)

        hive.trigger(i.pull_position, i.do_set_position)


Position = hive.dyna_hive("Position", build_position, declare_position, cls=PositionClass)