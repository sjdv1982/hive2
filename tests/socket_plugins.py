from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


class Dog(object):

    def print_house(self):
        print(self.get_house())

    def set_get_house(self, get_house_func):
        self.get_house = get_house_func


def build_dog(cls, i, ex, args):
    i.print_house = hive.modifier(cls.print_house)
    ex.print_house = hive.entry(i.print_house)
    ex.some_socket = hive.socket(cls.set_get_house)


class House(object):
    def get_current_hive(self):
        return self


def build_house(cls, i, ex, args):
    # method 1
    i.dog = DogHive()
    ex.dog = i.dog

    i.some_plugin = hive.plugin(cls.get_current_hive)
    hive.connect(i.some_plugin, i.dog.some_socket)

    # # method 2
    # i.brutus = DogHive("Brutus")
    # i.fifi = DogHive("Fifi")
    # #and connection happens automatically


DogHive = hive.hive("DogHive", build_dog, Dog)
HouseHive = hive.hive("HouseHive", build_house, House)

house = HouseHive()
house.dog.print_house()
