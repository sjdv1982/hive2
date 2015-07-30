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
    i.print_house = hive.triggerable(cls.print_house)
    ex.print_house = hive.entry(i.print_house)
    ex.some_socket = hive.socket(cls.set_get_house, identifier=("a", "b"), data_type="float", auto_connect=True)


class House(object):
    def get_current_hive(self):
        return self


def build_house(cls, i, ex, args):
    ex.some_plugin = hive.plugin(cls.get_current_hive, identifier=("a", "b"), data_type="float",
                                 policy_cls=hive.plugin_policies.MultipleOptional,
                                 auto_connect=True)

    # Auto connect
    i.brutus = DogHive(auto_connect=True)
    ex.brutus = hive.hook(i.brutus)

    # Manual connect
    i.fido = DogHive()

    ex.fido = hive.hook(i.brutus)
    hive.connect(ex.some_plugin, i.fido.some_socket)


DogHive = hive.hive("DogHive", build_dog, Dog)
HouseHive = hive.hive("HouseHive", build_house, House)

house = HouseHive()

house.brutus.print_house()
house.fido.print_house()