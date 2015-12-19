from dragonfly.instance import Instantiator
from dragonfly.event import EventHive
from dragonfly.gen import Next
from dragonfly.std import Variable

import hive
import dragonfly


def build_some_instance(i, ex, args):
    args.some_param = hive.parameter("int")
    i.some_var = hive.attribute("int", args.some_param)
    ex.on_tick = dragonfly.event.Tick()
    i.mod = hive.modifier(lambda self: print(self._some_var))
    hive.connect(ex.on_tick, i.mod)


SomeHive = hive.hive("SomeHive", build_some_instance)
import sys
sys.modules['this.that'] = type("", (), {'other': SomeHive})


def build_my_hive(i, ex, args):
    ex.events = EventHive()
    ex.instantiator = Instantiator(cls_import_path="this.that.other")

    # Create args dict
    i.args = Variable("dict", {'some_param': 12})
    hive.connect(i.args, ex.instantiator)

    # Create bind id getter
    i.bind_id_getter = Next(("str", "id"))
    i.gen = Variable("object", iter(range(1000)))
    hive.connect(i.gen, i.bind_id_getter)
    hive.connect(i.bind_id_getter, ex.instantiator.bind_id)


MyHive = hive.hive("MyHive", build_my_hive)
my_hive = MyHive()

my_hive.instantiator.create()
instance = my_hive.instantiator.last_created

# Push some event to first hive instance
print("For hive 1, expect 12")
my_hive.events.read_event.plugin()((0, "tick",))

print("Now hive 2, expect 99")

my_hive._args.data['some_param'] = 99
my_hive.instantiator.create()

my_hive.events.read_event.plugin()((1, "tick",))