import hive


class EntityClass:

    def __init__(self):
        self._get_entity = None

        self.entity = None
        self.identifier = None

    def set_get_entity(self, get_entity):
        self.get_entity = get_entity

    def do_get_entity(self):
        self.entity = self._get_entity(self.identifier)


def build_get_entity(cls, i, ex, args):
    """Get entity from scene by ID"""
    ex.get_get_entity = hive.socket(cls.set_get_entity, identifier="entity.get")

    i.identifier = hive.property(cls, "identifier", "str.id")
    i.pull_identifier = hive.pull_in(i.identifier)
    ex.identifier = hive.antenna(i.pull_identifier)

    i.entity = hive.property(cls, "entity", "entity")
    i.pull_entity = hive.pull_out(i.entity)
    ex.entity = hive.output(i.pull_entity)

    i.do_get_entity = hive.triggerable(cls.do_get_entity)

    hive.trigger(i.pull_entity, i.pull_identifier, pretrigger=True)
    hive.trigger(i.pull_entity, i.do_get_entity, pretrigger=True)


GetEntity = hive.hive("GetEntity", build_get_entity, cls=EntityClass)
