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


def build_physics_manager(cls, i, ex, args):
    i.tick_rate = hive.property(cls, "tick_rate", 'int')
    i.pull_tick_rate = hive.pull_in(i.tick_rate)
    ex.tick_rate = hive.antenna(i.pull_tick_rate)

    i.do_update = hive.triggerfunc(cls.update)
    hive.trigger(i.do_update, i.pull_tick_rate, pretrigger=True)

    i.on_tick = hive.triggerable(i.do_update)
    ex.tick = hive.entry(i.on_tick)


PhysicsManager = hive.hive("PhysicsManager", build_physics_manager, cls=_PhysicsManagerClass)