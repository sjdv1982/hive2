import hive


class _PhysicsManagerClass:

    def __init__(self):
        from panda3d.bullet import BulletWorld
        self._world = BulletWorld()
        self._world.set_gravity(0, 0, -9.807)

        self.tick_rate = None

    def add_rigid_body(self, rigid_body):
        self._world.attach_rigid_body(rigid_body)

    def remove_rigid_body(self, rigid_body):
        self._world.remove_rigid_body(rigid_body)

    def update(self):
        self._world.do_physics(1/self.tick_rate)

    def register_entity(self, name, entity):
        rb = entity.find("**-BulletRigidBodyNode")
        print(rb)


def build_physics_manager(cls, i, ex, args):
    i.tick_rate = hive.property(cls, "tick_rate", 'int')
    i.pull_tick_rate = hive.pull_in(i.tick_rate)
    ex.tick_rate = hive.antenna(i.pull_tick_rate)

    i.do_update = hive.triggerfunc(cls.update)
    hive.trigger(i.do_update, i.pull_tick_rate, pretrigger=True)

    i.on_tick = hive.triggerable(i.do_update)
    ex.tick = hive.entry(i.on_tick)

    ex.get_register_entity = hive.plugin(cls.register_entity, "entity.register_template")


PhysicsManager = hive.hive("PhysicsManager", build_physics_manager, cls=_PhysicsManagerClass)