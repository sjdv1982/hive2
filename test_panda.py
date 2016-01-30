#!/usr/bin/env python

"""
Playing around with QMainWindow's nested within each other
as dock widgets.
"""

from random import randint

try:
    from PySide import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui

# Set to False - Standard docking of widgets around the main content area
# Set to True - Sub MainWindows each with their own private docking
DO_SUB_DOCK_CREATION = False


_DOCK_OPTS = QtGui.QMainWindow.AnimatedDocks
_DOCK_OPTS |= QtGui.QMainWindow.AllowNestedDocks
_DOCK_OPTS |= QtGui.QMainWindow.AllowTabbedDocks

_DOCK_COUNT = 0
_DOCK_POSITIONS = (
    QtCore.Qt.LeftDockWidgetArea,
    QtCore.Qt.TopDockWidgetArea,
    QtCore.Qt.RightDockWidgetArea,
    QtCore.Qt.BottomDockWidgetArea
)

def main():
    mainWindow = QtGui.QMainWindow()
    mainWindow.resize(1024,768)
    mainWindow.setDockOptions(_DOCK_OPTS)

    widget = QtGui.QLabel("MAIN APP CONTENT AREA")
    widget.setMinimumSize(300,200)
    widget.setFrameStyle(widget.Box)
    mainWindow.setCentralWidget(widget)

    addDocks(mainWindow, "Main Dock")

    mainWindow.show()
    mainWindow.raise_()

    return mainWindow


def addDocks(window, name, subDocks=True):
    global _DOCK_COUNT

    for pos in _DOCK_POSITIONS:

        for _ in range(2):
            _DOCK_COUNT += 1

            sub = QtGui.QMainWindow()
            sub.setWindowFlags(QtCore.Qt.Widget)
            sub.setDockOptions(_DOCK_OPTS)

            color = tuple(randint(20, 230) for _ in range(3))

            label = QtGui.QLabel("%s %d content area" % (name, _DOCK_COUNT), sub)
            label.setMinimumHeight(25)
            label.setStyleSheet("background-color: rgb(%d, %d, %d)" % color)
            sub.setCentralWidget(label)

            dock = QtGui.QDockWidget("%s %d title bar" % (name, _DOCK_COUNT))
            dock.setWidget(sub)

            if DO_SUB_DOCK_CREATION and subDocks:
                addDocks(sub, "Sub Dock", subDocks=False)

            window.addDockWidget(pos, dock)


if __name__ == "__main__":
    app = QtGui.QApplication([])
    mainWindow = main()
    app.exec_()

# from test.panda_project.basic_keyboard import BasicKeyboard as SomePandaDemo
#
# import dragonfly
# import hive
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
# from hive.debug import current_context_as
# from editor.debugging import HivemapDebugContext
#
#
# MyHive = dragonfly.app.panda3d.Mainloop.extend("MyHive", build_my_hive, builder_cls=MyHiveClass)
#
# # serv = Server()
# # serv.launch()
#
# debug = HivemapDebugContext()
# with current_context_as(debug):
#     my_hive = MyHive()
#     my_hive.run()
#
# #
# # import hive
# #
# #
# # class BClass:
# #
# #     @hive.types(name="str")
# #     def do(self, name):
# #         print("DO", self,name)
# #
# #
# # def build(cls, i, ex, args):
# #     i.pin = hive.push_in(cls.do)
# #     ex.inp = hive.antenna(i.pin)
# #
# #
# # HIN = hive.hive("H", build, BClass)
# #
# #
# # class BClass:
# #
# #     @hive.return_type("str")
# #     def do(self):
# #         return "BOBBY"
# #
# #     @property
# #     @hive.return_type("str")
# #     def prop(self):
# #         return "SOME"
# #
# #
# # def build(cls, i, ex, args):
# #     i.pin = hive.push_out(cls.do)
# #     ex.inp = hive.output(i.pin)
# #
# #     i.input2 = hive.push_out(cls.prop)
# #     ex.inp2 = hive.output(i.input2)
# #
# #     i.prop = hive.property(cls, "prop", "str")
# #     i.input3 = hive.push_out(i.prop)
# #     ex.inp3 = hive.output(i.input3)
# #     #ex.do = cls.do
# #
# #
# # HOUT = hive.hive("H", build, BClass)
# #
# # h1 = HOUT()
# # h2 = HIN()
# # print(h1.inp.data_type)
# # hive.connect(h1.inp, h2.inp)
# # hive.connect(h1.inp2, h2.inp)
# # hive.connect(h1.inp3, h2.inp)
# # h1.inp.push()
# # h1.inp2.push()
# # h1.inp3.push()