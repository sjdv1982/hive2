import sys
sys.path.append("D:/bzr")

import spyder

import model
map = model.Hivemap([], [], [0, 0])

print(map.bees, map.parameters)


class Hive:

    def __init__(self, name):
        self.bees = []
        self.name = name

    def __repr__(self):
        return "<Hive: {}>".format(self.name)


class Bee:
    pass


class Trigger(Bee):
    pass


outer = Hive("Outer")
inner = Hive("Inner")
trigger = Trigger()

outer.bees.append(inner)
outer.bees.append(trigger)

print(outer.bees , inner)