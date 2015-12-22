import hive

from ..instance import Instantiator


class SpawnClass:

    def __init__(self):
        self._spawn_entity = None

        self.entity_class = None
        self.spawn_id = None

        self.entity_last_created = None

    def set_spawn_entity(self, spawn_entity):
        self._spawn_entity = spawn_entity

    def do_spawn_entity(self):
        self.entity_last_created = self._spawn_entity(self.entity_class, self.spawn_id)


def build_spawn(cls, i, ex, args):
    ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, ("entity", "spawn"))

    i.entity_class = hive.property(cls, "entity_class", ("str", "id"))
    i.pull_class = hive.pull_in(i.entity_class)
    ex.entity_class = hive.antenna(i.pull_class)

    i.spawn_id = hive.property(cls, "spawn_id", ("str", "id"))
    i.pull_spawn_id = hive.pull_in(i.spawn_id)
    ex.spawn_id = hive.antenna(i.pull_spawn_id)

    i.entity_last_created = hive.property(cls, "entity_last_created", "entity")
    i.pull_entity = hive.pull_out(i.entity_last_created)
    ex.entity_last_created = hive.output(i.pull_entity)

    i.do_spawn = hive.triggerable(cls.do_spawn_entity)
    i.trigger = hive.triggerfunc(i.do_spawn)
    i.on_triggered = hive.triggerable(i.trigger)

    hive.trigger(i.trigger, i.pull_class, pretrigger=True)
    hive.trigger(i.trigger, i.pull_spawn_id, pretrigger=True)

    i.pull_out_spawn_id = hive.pull_out(i.spawn_id)

    # Process instantiator
    i.instantiator = Instantiator()
    hive.connect(i.pull_out_spawn_id, i.instantiator.bind_id)
    hive.connect(i.pull_entity, i.instantiator.entity)

    # Get last created
    ex.hive_last_created = hive.output(i.instantiator.last_created)

    # Finally instantiate
    hive.trigger(i.trigger, i.instantiator.create)

    ex.spawn = hive.entry(i.on_triggered)


Spawn = hive.hive("Spawn", build_spawn, cls=SpawnClass)