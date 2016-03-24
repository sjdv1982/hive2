# # import hive
# # import hive_gui.utils as utils
# # #
# # # MyHive = utils.class_from_filepath("D:/hivedemo/my_iter.hivemap")
# # #
# # # my_hive = MyHive()
# # # my_hive.do_iter()
# # #
# # MyHive = utils.class_from_filepath("D:/hivedemo/example.hivemap")
# #
# # my_hive = MyHive()
# # print("BEFORE")
# # my_hive.start_counting()
# # print("AFTER")
#
#
# import os
# import sys
#
# current_directory = os.path.split(os.path.abspath(__file__))[0]
# sys.path.append(current_directory + "/" + "..")
#
# import hive
#
#
# def get_last(n, a):
#     while True:
#         if not hasattr(n, a):
#             return n
#         n = getattr(n, a)
#
#
# class C:
#     def __init__(self, name="<internal>"):
#         self.name = name
#
#     def print_name(self):
#         print("NAME =", self.name)
#
#     def get_plug(self, o):
#         o()
#
#
# def build_h(cls, i, ex, args, meta_args):
#     print("Build hive", meta_args.i)
#
#     is_root = meta_args.root
#
#     if is_root:
#         print("IS ROOT")
#         ex.plug = hive.plugin(cls.print_name, identifier="some_api.func")
#
#     if meta_args.i:
#         ex.h = SomeHive(i=meta_args.i-1, root=False, name="<internal>", import_namespace=True)
#
#     else:
#         ex.sock = hive.socket(cls.get_plug, identifier="some_api.func")
#
#     # if is_root and 0:
#     #     hive.connect(ex.plug, get_last(ex, "h").sock)
#
#
# def declare_h(meta_args):
#     meta_args.i = hive.parameter("int", 3)
#     meta_args.root = hive.parameter("bool", True)
#
# SomeHive = hive.dyna_hive("H1", build_h, builder_cls=C, declarator=declare_h)
#
# # This works
# h1 = SomeHive(name="OtherHive")
#
# # This doesn't
# h2 = SomeHive(name="OtherHive2")
#
# #print(h2.h.h.sock is h1.h.h.sock)




# Imports
import dragonfly.io
import hive
import dragonfly.event
import hive_editor
import dragonfly.std
import dragonfly.gen


def builder(i, ex, args):
    # Declarations
    i.print = dragonfly.io.Print()
    i.for_each = dragonfly.gen.ForEach(data_type='int')
    i.max_value = dragonfly.std.Variable(data_type='int', start_value=11)
    i.on_start = dragonfly.event.OnStart()
    i.min_value = dragonfly.std.Variable(data_type='int', start_value=0)
    i.step = dragonfly.std.Variable(data_type='int', start_value=1)
    i.range = dragonfly.gen.Range()

    # Connectivity
    hive.connect(i.for_each.value_out, i.print.value_in)
    hive.connect(i.max_value.value_out, i.range.max_value)
    hive.trigger(i.on_start.on_started, i.for_each.trig_in, pretrigger=False)
    hive.connect(i.min_value.value_out, i.range.min_value)
    hive.connect(i.step.value_out, i.range.step)
    hive.connect(i.range.iterator, i.for_each.iterable)


from dragonfly.event import EventHive

H = EventHive.extend("E", builder)
h = H()
h.event_in.push(("start",))