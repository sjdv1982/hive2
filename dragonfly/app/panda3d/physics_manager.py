import hive


class _PhysicsManagerClass:

    def __init__(self):
        from panda3d.bullet import BulletWorld
        self._world = BulletWorld()
        self._world.set_gravity(0, 0, -9.807)

        self.tick_rate = None
        self.time = 0.0

    def add_rigid_body(self, rigid_body):
        self._world.attach_rigid_body(rigid_body)

    def remove_rigid_body(self, rigid_body):
        self._world.remove_rigid_body(rigid_body)

    def update(self):
        self._world.do_physics(1/self.tick_rate)
        self.time += 1/self.tick_rate

    def get_velocity_absolute(self, rb):
        node = rb # TODO
        return tuple(node.get_linear_velocity())

    def set_velocity_absolute(self, rb, vel):
        node = rb # TODO
        return node.set_linear_velocity(*vel)

    @hive.types(entity='entity')
    def on_entity_spawned(self, entity):
        parent = entity.get_parent()
        nodepath = parent.find("+BulletRigidBodyNode")
        self._world.attach_rigid_body(nodepath.node())
        print("ADD")

    @hive.types(entity='entity')
    def on_entity_destroyed(self, entity):
        parent = entity.get_parent()
        nodepath = parent.find("+BulletRigidBodyNode")
        self._world.remove_rigid_body(nodepath.node())


def build_physics_manager(cls, i, ex, args):
    i.tick_rate = hive.property(cls, "tick_rate", 'int')
    i.pull_tick_rate = hive.pull_in(i.tick_rate)
    ex.tick_rate = hive.antenna(i.pull_tick_rate)

    i.do_update = hive.triggerfunc(cls.update)
    hive.trigger(i.do_update, i.pull_tick_rate, pretrigger=True)

    i.on_tick = hive.triggerable(i.do_update)
    ex.tick = hive.entry(i.on_tick)

    i.push_entity_spawned = hive.push_in(cls.on_entity_spawned)
    ex.on_entity_spawned = hive.antenna(i.push_entity_spawned)

    i.push_entity_destroyed = hive.push_in(cls.on_entity_destroyed)
    ex.on_entity_destroyed = hive.antenna(i.push_entity_destroyed)


PhysicsManager = hive.hive("PhysicsManager", build_physics_manager, builder_cls=_PhysicsManagerClass)