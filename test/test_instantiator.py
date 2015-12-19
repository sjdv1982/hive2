from dragonfly.instance import Instantiator
from dragonfly.event import EventHive
from dragonfly.gen import Next
from dragonfly.std import Variable

import hive


def build_my_hive(i, ex, args):
    ex.events = EventHive()
    ex.instantiator = Instantiator(cls_import_path="dragonfly.event.Tick", bind_event=False)
    i.bind_id_getter = Next(("str", "id"))
    i.gen = Variable("object", iter(range(1000)))
    hive.connect(i.gen, i.bind_id_getter)
    hive.connect(i.bind_id_getter, ex.instantiator.bind_id)

MyHive = hive.hive("MyHive", build_my_hive)
my_hive = MyHive()

my_hive.instantiator.create()
h = my_hive.instantiator.last_created

do_trig = hive.triggerable(lambda: print("TRUGGERd"))
hive.trigger(h.hive.on_tick, do_trig)

h.read_event.plugin()((0, "tick",))