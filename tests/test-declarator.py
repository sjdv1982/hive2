from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


def build_dog(i, ex, args):
    for ix in range(args.puppies):
        mod = hive.modifier(lambda h, ix=ix: print("Puppy {} barked".format(ix)))
        setattr(i, "mod_{}".format(ix), mod)
        setattr(ex, "bark_{}".format(ix), hive.entry(mod))

    print(i)
    print(ex)
    print(args)


def declarator_dog(args):
    args.puppies = hive.parameter(("int",), 1)
    print(args)


DogHive = hive.hive("Dog", build_dog, declarator=declarator_dog)


d = DogHive(puppies=2)
d.bark_0()
d.bark_1()