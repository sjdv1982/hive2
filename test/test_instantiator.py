from dragonfly.instance import Instantiator
from dragonfly.event import EventHive
from dragonfly.gen import Next
from dragonfly.std import Variable

import hive
import dragonfly


def build_some_instance(i, ex, args):
    args.name = hive.parameter("str")
    i.some_var = hive.attribute("str", args.name)
    ex.on_tick = dragonfly.event.Tick()
    i.mod = hive.modifier(lambda self: print(self, self._some_var))
    hive.connect(ex.on_tick, i.mod)


SomeHive = hive.hive("SomeHive", build_some_instance)
import sys
sys.modules['this.that'] = type("", (), {'other': SomeHive})


def build_my_hive(i, ex, args):
    ex.events = EventHive()

    # Create instantiator, but don't add events by leader
    ex.instantiator = Instantiator(cls_import_path="this.that.other",
                                   event_dispatch_mode='all')

    # Create args dict
    i.args = Variable("dict", {'name': 'a'})
    hive.connect(i.args, ex.instantiator)

    # Create bind id getter
    i.bind_id_getter = Next(("str", "id"))
    i.gen = Variable("object", iter(range(1000)))
    hive.connect(i.gen, i.bind_id_getter)
    hive.connect(i.bind_id_getter, ex.instantiator.bind_id)


MyHive = hive.hive("MyHive", build_my_hive)
my_hive = MyHive()

my_hive.instantiator.create()
a = my_hive.instantiator.last_created

my_hive._args.data['name'] = 'b'
my_hive.instantiator.create()
b = my_hive.instantiator.last_created

my_hive._args.data['name'] = 'c'
my_hive.instantiator.create()
c = my_hive.instantiator.last_created

my_hive.events.read_event.plugin()(("tick",))
print("Closing A!")
a.close()

my_hive.events.read_event.plugin()(("tick",))