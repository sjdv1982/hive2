from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


class Dog(object):

    def __init__(self):
        self.woof_count = 0


def build_dog(cls, i, ex, args):
    i.mod = hive.modifier(lambda h: print("HI"))
    ex.mod = hive.entry(i.mod)


def declarator_dog(args):
    pass


DogHive = hive.hive("Dog", build_dog, Dog, declarator_dog)


d = DogHive()
d.mod()