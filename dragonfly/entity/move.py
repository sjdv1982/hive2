import hive


class MoveClass:

    def __init__(self):
        self.displacement = None
        self.entity = None
        self.other_entity = None

        self._get_position = None
        self._set_position = None
        self._get_entity = None

    def do_get_entity(self):
        self.entity = self._get_entity()

    def do_move_absolute(self):
        entity = self.entity

        new_position = self._get_position(entity) + self.displacement
        self._set_position(entity, new_position)

    def do_move_relative(self):
        entity = self.entity
        other_entity = self.other_entity

        new_position = self._get_position(entity, other_entity) + self.displacement
        self._set_position(entity, other_entity, new_position)

    def set_get_position(self, get_position):
        self._get_position = get_position

    def set_set_position(self, set_position):
        self._set_position = set_position

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def declare_move(meta_args):
    meta_args.bound = hive.parameter("bool", False)
    meta_args.coordinate_system = hive.parameter("str", 'absolute', options={'absolute', 'relative'})
    # TODO advanced: if relative, allow choose to_self to disable input (or maybe use bool)


def build_move(cls, i, ex, args, meta_args):
    """Apply a position delta to an entity"""
    coordinate_system = meta_args.coordinate_system

    i.displacement = hive.property(cls, "displacement", "vector")
    i.pull_displacement = hive.pull_in(i.displacement)
    ex.displacement = hive.antenna(i.pull_displacement)

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier="entity.get_bound")
        i.do_get_entity = hive.triggerable(cls.do_get_entity)

        hive.trigger(i.pull_displacement, i.do_get_entity)

    else:
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)

        hive.trigger(i.pull_displacement, i.pull_entity)

    if coordinate_system == 'absolute':
        ex.get_set_position = hive.socket(cls.set_set_position, identifier="entity.position.set.absolute")
        ex.get_get_position = hive.socket(cls.set_get_position, identifier="entity.position.get.absolute")

        i.do_set_position = hive.triggerable(cls.do_move_absolute)

    else:
        i.other_entity = hive.property(cls, "other_entity", "entity")
        i.pull_other_entity = hive.pull_in(i.other_entity)
        ex.other_entity = hive.antenna(i.pull_other_entity)

        hive.trigger(i.pull_displacement, i.pull_other_entity)

        ex.get_set_position = hive.socket(cls.set_set_position, identifier="entity.position.set.relative")
        ex.get_get_position = hive.socket(cls.set_get_position, identifier="entity.position.get.relative")

        i.do_set_position = hive.triggerable(cls.do_move_relative)

    hive.trigger(i.pull_displacement, i.do_set_position)

    ex.trig = hive.entry(i.pull_displacement)


Move = hive.dyna_hive("Move", build_move, declare_move, builder_cls=MoveClass)