# import hive
# import dragonfly
#
# import gui
# from test.panda_project.some_panda_demo import SomePandaDemo
#
#
# class MyHiveClass:
#
#     def set_register_template(self, register_template):
#         cube = loader.loadModel("cube.egg")
#         register_template("cube", cube)
#
#     def set_spawn_entity(self, spawn_entity):
#         self._spawn_entity = spawn_entity
#
#     def spawn(self, template_name):
#         return self._spawn_entity(template_name)
#
#
# def build_my_hive(cls, i, ex, args):
#     ex.get_spawn_entity = hive.socket(cls.set_spawn_entity, identifier="entity.spawn")
#     ex.get_register_template = hive.socket(cls.set_register_template, "entity.register_template")
#
#     i.some_panda_hive = SomePandaDemo()
#
#
# MyHive = dragonfly.app.panda3d.Mainloop.extend("MyHive", build_my_hive, builder_cls=MyHiveClass)
# my_hive = MyHive()
#
# my_hive.run()

import hive


class BClass:

    @hive.types(name="str")
    def do(self, name):
        print("DO", self,name)


def build(cls, i, ex, args):
    i.pin = hive.push_in(cls.do)
    ex.inp = hive.antenna(i.pin)


HIN = hive.hive("H", build, BClass)


class BClass:

    @hive.return_type("str")
    def do(self):
        return "BOBBY"

    @property
    @hive.return_type("str")
    def prop(self):
        return "SOME"


def build(cls, i, ex, args):
    i.pin = hive.push_out(cls.do)
    ex.inp = hive.output(i.pin)

    i.input2 = hive.push_out(cls.prop)
    ex.inp2 = hive.output(i.input2)

    i.prop = hive.property(cls, "prop", "str")
    i.input3 = hive.push_out(i.prop)
    ex.inp3 = hive.output(i.input3)
    #ex.do = cls.do


HOUT = hive.hive("H", build, BClass)

h1 = HOUT()
h2 = HIN()
print(h1.inp.data_type)
hive.connect(h1.inp, h2.inp)
hive.connect(h1.inp2, h2.inp)
hive.connect(h1.inp3, h2.inp)
h1.inp.push()
h1.inp2.push()
h1.inp3.push()