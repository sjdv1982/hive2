import dragonfly
import hive

import hive_editor

from hive_editor.debugging.network import NetworkDebugContext
from example_calc import ExampleCalc


class MyHiveClass:
    pass


def build_my_hive(cls, i, ex, args):
    i.main_hive = ExampleCalc()


MyHive = dragonfly.panda3d.Mainloop.extend("MyHive", build_my_hive, builder_cls=MyHiveClass)

DO_DEBUG = True

if DO_DEBUG:
    debug_context = NetworkDebugContext()
    with debug_context:
        my_hive = MyHive()
        my_hive.run()
else:
    my_hive = MyHive()
    my_hive.run()