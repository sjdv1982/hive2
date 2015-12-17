# Imports
import sys

import bge

# Add the hive2 directory to sys.path
sys.path.append(bge.logic.expandPath("//../../"))

import hive
import dragonfly
from dragonfly.app.blender.input_handler import InputHandler


try:
    import bpy
except ImportError:
    pass

else:
    import gui.importer as importer
    def del_hook(ctx):
        importer.uninstall_hook()

    bpy.app.handlers.game_post[:] = [del_hook]


# Import hivemap
from some_bge_demo import SomeBgeDemo as TestHive


class MyHive_:
    
    def __init__(self):
        self._read_event = None

        self.input_handler = InputHandler()
    
    def set_read_event(self, read_event):
        self._read_event = read_event
        self.input_handler.add_listener(read_event)

        self.read_event(("start",))
    
    def read_event(self, event):
        self._read_event(event)

    def tick(self):
        self.input_handler.update_events()
        self.read_event(("tick",))


def build_my_hive(cls, i, ex, args):
    ex.get_read_event = hive.socket(cls.set_read_event)
    hive.connect(ex.read_event, ex.get_read_event)
        
    i.read_event = hive.push_in(cls.read_event)
    ex.event_in = hive.antenna(i.read_event)
    
    i.hive = TestHive()

    i.tick = hive.triggerable(cls.tick)
    ex.tick = hive.entry(i.tick)
 
 
# Add support to manually pass events to the hive without using a mainloop
MyHive = dragonfly.event.EventHive.extend("Events", build_my_hive, builder_cls=MyHive_)
my_hive = MyHive()


def tick():
    my_hive.tick()
