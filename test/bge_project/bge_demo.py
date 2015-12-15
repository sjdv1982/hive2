import sys

# Add the hive2 directory to sys.path
import bge
sys.path.append(bge.logic.expandPath("//../../"))

try:
    import bpy
except ImportError:
    pass

else:
    import hive_gui.importer as importer
    def del_hook(ctx):
        importer.uninstall_hook()

    bpy.app.handlers.game_post[:] = [del_hook]

# Imports
import hive


class MyHive_:
    
    def __init__(self):
        self._read_event = None
    
    def set_read_event(self, read_event):
        self._read_event = read_event
    
    def read_event(self, event):
        self._read_event(event)


# Import hivemap
from some_bge_demo import SomeBgeDemo as TestHive

def build_my_hive(cls, i, ex, args):
    ex.get_read_event = hive.socket(cls.set_read_event)
    hive.connect(ex.read_event, ex.get_read_event)
        
    i.read_event = hive.push_in(cls.read_event)
    ex.event_in = hive.antenna(i.read_event)
    
    i.hive = TestHive()
 
 
# Add support to manually pass events to the hive without using a mainloop 
import dragonfly
MyHive = dragonfly.event.EventHive.extend("Events", build_my_hive, builder_cls=MyHive_)


import bge

my_hive = MyHive()
my_hive.event_in.push(("start",))

def tick():
    new_events = []
    done_events = []
    
    for event, event_state in bge.logic.keyboard.active_events.items():
        event_name = bge.events.EventToString(event).lower().replace("key", "")
        
        if event_state == bge.logic.KX_INPUT_JUST_ACTIVATED:
            my_hive.event_in.push(("keyboard", "pressed", event_name))
            
        elif event_state == bge.logic.KX_INPUT_JUST_RELEASED:
            my_hive.event_in.push(("keyboard", "released", event_name))
                
    my_hive.event_in.push(("tick",))