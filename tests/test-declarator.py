from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


def build_dog(i, ex, args):
    print("Invoked Builder")
    for ix in range(args.puppies):
        mod = hive.modifier(lambda h, ix=ix: print("Puppy {} barked".format(ix)))
        setattr(i, "mod_{}".format(ix), mod)
        setattr(ex, "bark_{}".format(ix), hive.entry(mod))


def declarator_dog(args):
    print("Invoked Declarator")
    args.puppies = hive.parameter(("int",), 1)


DogHive = hive.hive("Dog", build_dog, declarator=declarator_dog)


d = DogHive(puppies=2)
d.bark_0()
d.bark_1()

d = DogHive(puppies=1)
d.bark_0()

print(dir(d))