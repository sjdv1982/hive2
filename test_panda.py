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


def build_my_hive(cls, i, ex, args):
    ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, identifier=("entity", "spawn"))
    ex.get_register_template = hive.socket(cls.set_register_template, ("entity", "register_template"))

    i.some_panda_hive = SomePandaDemo()

MyHive = dragonfly.app.panda3d.Mainloop.extend("MyHive", build_my_hive, builder_cls=MyHiveClass)
my_hive = MyHive()

my_hive.run()
