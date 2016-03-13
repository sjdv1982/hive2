import dragonfly
import hive

from hive_editor.debugging.network import NetworkDebugContext
from panda_project.launcher import Launcher


class MyHiveClass:

    def set_register_template(self, register_template):
        cube = loader.loadModel("panda_project/cube.egg")
        register_template("cube", cube)

    def set_spawn_entity(self, spawn_entity):
        self._spawn_entity = spawn_entity

    def spawn(self, template_name):
        print("SPAN", template_name )
        return self._spawn_entity(template_name)


def build_my_hive(cls, i, ex, args):
    ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, identifier="entity.spawn")
    ex.get_register_template = hive.socket(cls.set_register_template, "entity.register_template")

    i.main_hive = Launcher()


MyHive = dragonfly.app.panda3d.Mainloop.extend("MyHive", build_my_hive, builder_cls=MyHiveClass)

DO_DEBUG = False

if DO_DEBUG:
    debug_context = NetworkDebugContext()
    with debug_context:
        my_hive = MyHive()
        my_hive.run()
else:
    my_hive = MyHive()
    my_hive.run()