import hive

from .instantiate import Instantiator


class SpawnClass:

    def __init__(self):
        self._spawn_entity = None
        self._register_destructor = None

        self.entity_class = None
        self.entity_last_created = None

        self._hive = hive.get_run_hive()

    def set_spawn_entity(self, spawn_entity):
        self._spawn_entity = spawn_entity

    def do_spawn_entity(self):
        self.entity_last_created = self._spawn_entity(self.entity_class)

    def on_entity_process_created(self, process_id, entity_hive):
        destructor = lambda: self._hive._instantiator.stop_process.push(process_id)
        self._register_destructor(self.entity_last_created, destructor)

    def set_register_destructor(self, register_destructor):
        self._register_destructor = register_destructor


def declare_spawn(meta_args):
    meta_args.spawn_hive = hive.parameter("bool", True)


def build_spawn(cls, i, ex, args, meta_args):
    """Spawn an entity into the scene"""
    ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, "entity.spawn")

    # Associate entity with this hive so it is safely destroyed
    ex.get_register_destructor = hive.socket(cls.set_register_destructor, "entity.register_destructor")
    ex.on_entity_process_instantiated = hive.plugin(cls.on_entity_process_created, "bind.on_created")

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
        i.instantiator = Instantiator(forward_events='all', bind_process='child')

        # Pull entity to instantiator
        hive.connect(i.pull_entity, i.instantiator.entity)

        # Get last created
        ex.hive_class = hive.antenna(i.instantiator.hive_class)
        ex.last_process_id = hive.output(i.instantiator.last_process_id)
        ex.stop_process = hive.antenna(i.instantiator.stop_process)
        ex.pause_events = hive.antenna(i.instantiator.pause_events)
        ex.resume_events = hive.antenna(i.instantiator.resume_events)

        # Instantiate
        hive.trigger(i.trigger, i.instantiator.create)

    else:
        # Finally push out entity
        hive.trigger(i.trigger, i.push_entity)

    ex.spawn = hive.entry(i.on_triggered)


Spawn = hive.dyna_hive("Spawn", build_spawn, declarator=declare_spawn, builder_cls=SpawnClass)
