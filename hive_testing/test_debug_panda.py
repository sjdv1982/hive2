import dragonfly
import hive

from hive_editor.debugging.network import NetworkDebugContext
from panda_project.launcher import Launcher


def create_cube():
    entity = loader.loadModel("panda_project/cube.egg")
    from panda3d.bullet import BulletBoxShape, BulletRigidBodyNode
    from panda3d.core import NodePath

    shape = BulletBoxShape((0.5, 0.5, 0.5))

    node = BulletRigidBodyNode('Box')
    node.setMass(1.0)
    node.addShape(shape)

    nodepath = NodePath(node)
    entity.wrt_reparent_to(nodepath)
    return nodepath
    # np = render.attachNewNode(node)
    # np.setPos(0, 0, 2)


class MyHiveClass:

    def __init__(self, tick_rate=60):
        self._templates = {'cube': create_cube()}

    def set_register_template(self, register_template):
        for name, entity in self._templates.items():
            register_template(name, entity)

    def set_spawn_entity(self, spawn_entity):
        self._spawn_entity = spawn_entity

    def spawn(self, template_name):
        print("SPAN", template_name )
        return self._spawn_entity(template_name)


def build_my_hive(cls, i, ex, args):
    ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, identifier="entity.spawn")
    ex.get_register_template = hive.socket(cls.set_register_template, "entity.register_template",
                                           policy=hive.MultipleRequired)

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