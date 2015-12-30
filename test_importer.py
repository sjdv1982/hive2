import hive
import dragonfly

from test.panda_project.some_panda_demo import SomePandaDemo


class MyHiveClass:

    def set_register_template(self, register_template):
        cube = loader.loadModel("cube.egg")
        register_template("cube", cube)

    def set_spawn_entity(self, spawn_entity):
        self._spawn_entity = spawn_entity

    def spawn(self, template_name):
        return self._spawn_entity(template_name)

    def on_started(self):
        # cube = self.spawn("cube")
        # cube.set_pos(0, 10, 0)
        # base.cam.look_at(cube)
        pass


def build_my_hive(cls, i, ex, args):
    ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, identifier=("entity", "spawn"))
    ex.get_register_template = hive.socket(cls.set_register_template, ("entity", "register_template"))

    ex.on_start = dragonfly.event.OnStart()
    i.on_started = hive.triggerable(cls.on_started)
    hive.trigger(ex.on_start, i.on_started)

    i.some_panda_hive = SomePandaDemo()

MyHive = dragonfly.app.panda3d.Mainloop.extend("MyHive", build_my_hive, builder_cls=MyHiveClass)
my_hive = MyHive()

# cube = loader.loadModel("cube.egg")
# cube.reparentTo(base.render)
#
# cube.set_pos(0, 10, 0)
# base.cam.look_at(cube)

my_hive.run()
