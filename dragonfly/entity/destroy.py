import hive


class DestroyClass:

    def __init__(self):
        self.entity = None

        self._destroy_entity = None
        self._get_entity = None

    def destroy(self):
        self._destroy_entity(self.entity)

    def do_get_entity(self):
        self.entity = self._get_entity()

    def set_get_entity(self, get_entity):
        self._get_entity = get_entity

    def set_destroy_entity(self, destroy_entity):
        self._destroy_entity = destroy_entity


def declare_destroy(meta_args):
    meta_args.bound = hive.parameter("bool", False)


def build_destroy(cls, i, ex, args, meta_args):
    """Apply a position delta to an entity"""
    i.trig_destroy = hive.triggerfunc(cls.destroy)
    i.do_destroy = hive.triggerable(i.trig_destroy)
    ex.destroy = hive.entry(i.do_destroy)

    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity, identifier="entity.get_bound")
        i.do_get_entity = hive.triggerable(cls.do_get_entity)

        hive.trigger(i.trig_destroy, i.do_get_entity, pretrigger=True)

    else:
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)

        hive.trigger(i.trig_destroy, i.pull_entity, pretrigger=True)

    ex.get_destroy_entity = hive.socket(cls.set_destroy_entity, identifier="entity.destroy")


Destroy = hive.dyna_hive("Destroy", build_destroy, declare_destroy, cls=DestroyClass)
