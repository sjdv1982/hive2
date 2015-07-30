from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


class Dog:

    def __init__(self, name):
        self.name = name


def build_dog(cls, i, ex, args):
    print("Invoked Builder")
    ex.name = hive.property(cls, "name")

    for ix in range(args.puppies):
        mod = hive.modifier(lambda h: print("Puppy {} barked".format(h.name)))
        setattr(i, "mod_{}".format(ix), mod)
        setattr(ex, "bark_{}".format(ix), hive.entry(mod))


def declarator_dog(args):
    print("Invoked Declarator")
    args.puppies = hive.parameter(("int",), 1)


DogHive = hive.hive("Dog", build_dog, Dog, declarator=declarator_dog)


d = DogHive(2, "Jack")
d.bark_0()
d.bark_1()

d = DogHive(1, "Jill")
d.bark_0()
