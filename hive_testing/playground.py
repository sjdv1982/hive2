# Imports
import dragonfly.std
import dragonfly.io
import hive_editor
import hive
import dragonfly.containers


def builder(i, ex, args):
    # Declarations
    i.unpack_tuple = dragonfly.containers.UnpackTuple(types=('str', 'int', 'float'))
    i.pack_tuple = dragonfly.containers.PackTuple(types=('str', 'int', 'float'))
    i.item_0 = dragonfly.std.Variable(data_type='str', start_value='a')
    i.transistor_1 = dragonfly.std.Transistor(data_type='str')
    i.print = dragonfly.io.Print()
    i.transistor = dragonfly.std.Transistor(data_type='tuple')
    i.item_2 = dragonfly.std.Variable(data_type='float', start_value=-0.1)
    i.item_1 = dragonfly.std.Variable(data_type='int', start_value=1)
    i.transistor_2 = dragonfly.std.Transistor(data_type='float')
    i.transistor_0 = dragonfly.std.Transistor(data_type='int')

    # Connectivity
    hive.connect(i.unpack_tuple.item_0, i.transistor_1.value)
    hive.connect(i.unpack_tuple.item_1, i.transistor_0.value)
    hive.connect(i.unpack_tuple.item_2, i.transistor_2.value)
    hive.connect(i.pack_tuple.tuple_, i.transistor.value)
    hive.connect(i.item_0.value_out, i.pack_tuple.item_0)
    hive.connect(i.transistor_1.result, i.print.value_in)
    hive.connect(i.transistor.result, i.unpack_tuple.tuple_)
    hive.trigger(i.transistor.result, i.transistor_1.trigger, pretrigger=False)
    hive.trigger(i.transistor.result, i.transistor_0.trigger, pretrigger=False)
    hive.trigger(i.transistor.result, i.transistor_2.trigger, pretrigger=False)
    hive.connect(i.item_2.value_out, i.pack_tuple.item_2)
    hive.connect(i.item_1.value_out, i.pack_tuple.item_1)
    hive.connect(i.transistor_2.result, i.print.value_in)
    hive.connect(i.transistor_0.result, i.print.value_in)

    # IO
    ex.entry = hive.entry(i.transistor.trigger)


Hive = hive.hive("Hive", builder)
h = Hive()
h.entry()