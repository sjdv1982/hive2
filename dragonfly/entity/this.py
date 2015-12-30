import hive


class ThisClass:

    def __init__(self):
        self._get_entity = None
        self.entity = None

    def get_entity(self):
        self.entity = self._get_entity()

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity


def build_this(cls, i, ex, args):
    """Access to current bound entity"""
    ex.get_bound_entity = hive.socket(cls.set_get_entity, identifier=("entity", "get_bound"))

    i.entity = hive.property(cls, "entity", "entity")
    i.pull_entity = hive.pull_out(i.entity)
    ex.entity = hive.output(i.pull_entity)

    i.do_get_entity = hive.triggerable(cls.get_entity)
    hive.trigger(i.pull_entity, i.do_get_entity, pretrigger=True)


This = hive.hive("This", build_this, cls=ThisClass)
