from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


def add_func(x, y):
    return x + y


class Dog(object):

    def __init__(self, name):
        self._hive = hive.get_run_hive()
        self.name = name
        self.a = 0
        self.b = 0


def build_dog(cls, i, ex, args):
    ex.a_ = hive.property(cls, "a")
    ex.b_ = hive.property(cls, "b")
    i.a_in = hive.push_in(ex.a_)
    i.b_in = hive.push_in(ex.b_)
    ex.a = hive.antenna(i.a_in)
    ex.b = hive.antenna(i.b_in)

    ex.ra = hive.attribute()
    i.r_out = hive.push_out(ex.ra)
    ex.o = hive.output(i.r_out)

    i.t = hive.modifier(lambda h: setattr(h, 'ra', (h.a_ + h.b_)))
    hive.trigger(i.a_in, i.t)

    ex.ca = hive.attribute()
    i.c_out = hive.push_out(ex.ca)

    i.do_output = hive.triggerfunc()
    ex.do_output = hive.hook(i.do_output)
    hive.trigger(i.do_output, i.c_out)

    ex.c = hive.output(i.c_out)
    

DogHive = hive.hive("dog", build_dog, Dog)

# Create runtime hive instances
spot = DogHive("Spot")
spike = DogHive("Spike")


hive.connect(spot.c, spike.a)
spot.ca = 12
spot.do_output()

spike.do_output()
print(spike.a_, spike.b_)
print(spike.ra, "CA")
#
# spot.call()
# spot.bark()
#
# spike.call()
# spike.bark()
