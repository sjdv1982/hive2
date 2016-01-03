import hive

from .instantiate import Instantiator


class SpawnClass:

    def __init__(self):
        self._spawn_entity = None

        self.entity_class = None
        self.entity_last_created = None

    def set_spawn_entity(self, spawn_entity):
        self._spawn_entity = spawn_entity

    def do_spawn_entity(self):
        self.entity_last_created = self._spawn_entity(self.entity_class, )


def declare_spawn(meta_args):
    meta_args.spawn_hive = hive.parameter("bool", True)


def build_spawn(cls, i, ex, args, meta_args):
    """Spawn an entity into the scene"""
    ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, ("entity", "spawn"))

    i.entity_class = hive.property(cls, "entity_class", "str.id")
    i.pull_class = hive.pull_in(i.entity_class)
    ex.entity_class = hive.antenna(i.pull_class)

    i.entity_last_created = hive.property(cls, "entity_last_created", "entity")

    if meta_args.spawn_hive:
        i.pull_entity = hive.pull_out(i.entity_last_created)
        ex.entity_last_created = hive.output(i.pull_entity)

    else:
        i.push_entity = hive.push_out(i.entity_last_created)
        ex.created_entity = hive.output(i.push_entity)

    i.do_spawn = hive.triggerable(cls.do_spawn_entity)
    i.trigger = hive.triggerfunc(i.do_spawn)
    i.on_triggered = hive.triggerable(i.trigger)

    hive.trigger(i.trigger, i.pull_class, pretrigger=True)

    # Process instantiator
    if meta_args.spawn_hive:
        i.instantiator = Instantiator(forward_events='all', bind_process='dependent')

        # Pull entity to instantiator
        hive.connect(i.pull_entity, i.instantiator.entity)

        # Get last created
        ex.hive_class = hive.antenna(i.instantiator.hive_class)
        ex.hive_last_created = hive.output(i.instantiator.last_created)

        # Instantiate
        hive.trigger(i.trigger, i.instantiator.create)

    else:
        # Finally push out entity
        hive.trigger(i.trigger, i.push_entity)

    ex.spawn = hive.entry(i.on_triggered)


Spawn = hive.dyna_hive("Spawn", build_spawn, declarator=declare_spawn, cls=SpawnClass)