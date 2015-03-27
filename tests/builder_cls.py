from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


class Dog(object):

    def __init__(self, name):
        self._hive = hive.get_run_hive()
        self.name = name
        self.woof_count = 0

    def call(self):
        print("Dog.call ({})".format(self.name))

    def woof(self):
        self.woof_count += 1
        print("Dog.woof ({}) [{}]".format(self.name, self.woof_count))
        self._hive.woofed()


def build_dog(cls, i, ex, args):
    i.call = hive.triggerfunc(cls.call)
    i.woof = hive.triggerable(cls.woof)
    hive.connect(i.call, i.woof)

    i.bark = hive.triggerfunc()
    hive.trigger(i.bark, i.woof)

    i.woof_only = hive.modifier(cls.woof)
    i.woofed = hive.triggerfunc()

    ex.woofs = hive.property(cls, "woofs")
    ex.woof = hive.entry(i.woof)
    ex.woof_only = hive.entry(i.woof_only)
    ex.woofed = hive.hook(i.woofed)
    ex.bark = hive.hook(i.bark)
    ex.call = hive.hook(i.call)
    

DogHive = hive.hive("dog", build_dog, Dog)

# Create runtime hive instances
spot = DogHive("Spot")
spike = DogHive("Spike")

spot.call()
spot.bark()

spike.call()
spike.bark()

spot.woof_only()