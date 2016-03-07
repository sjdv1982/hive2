import dragonfly
import hive

from contextlib import contextmanager
from hive.debug import FileDebugContext
from hive_editor.debugging.network import NetworkDebugContext
from panda_project.basic_keyboard import BasicKeyboard


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

    i.main_hive = BasicKeyboard()


MyHive = dragonfly.app.panda3d.Mainloop.extend("MyHive", build_my_hive, builder_cls=MyHiveClass)

@contextmanager
def no_context():
    yield
    return

if False:
    debug_context = NetworkDebugContext()

else:
    from io import StringIO
    as_file = StringIO()
    debug_context = FileDebugContext(as_file)

with debug_context:
    my_hive = MyHive()
    my_hive.run()


as_file.seek(0)
print(as_file.read(), "DART")