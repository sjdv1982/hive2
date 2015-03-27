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


class House(object):

    def dog_appeared(self):
        print("A wild dog appeared!")

    def mail_arrived(self):
        print("Mail arrives")


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


def build_house(cls, i, ex, args):
    i.brutus = DogHive("Brutus")
    i.fifi = DogHive("Fifi")

    i.dog_appeared = hive.triggerable(cls.dog_appeared)
    hive.trigger(i.brutus.call, i.dog_appeared)

    i.mail_arrived = hive.triggerfunc(cls.mail_arrived)
    hive.trigger(i.mail_arrived, i.fifi.woof)

    ex.brutus = i.brutus
    ex.fifi = i.fifi
    ex.mail_arrived = hive.hook(i.mail_arrived)
    ex.dog_appeared = hive.entry(i.dog_appeared)


DogHive = hive.hive("dog", build_dog, Dog)
HouseHive = hive.hive("House", build_house, House)

house = HouseHive()
house.mail_arrived()
house.brutus.call()
house.fifi.bark()
house.dog_appeared()


# def build_kennel(i, ex, args):
#     i.brutus = dog("Brutus")
#     i.fifi = dog("Fifi")
#     hive.trigger(i.fifi.call, i.brutus.woof)
#     #h.trigger(i.fifi.call, i.brutus)
#
# #underscore (_) names for brutus and fifi, since they are not in ex
#
# kennel = hive.hive("kennel", build_kennel)
# k = kennel()
# k2 = kennel()
#
# print(10)
# k._fifi.call() #=> CALL Fifi; WOOF Fifi 1; WOOF Brutus 1
#
# hive.connect(k._brutus.woofed, k._fifi.woof)
# #or: h.trigger(k.brutus.woofed, k.fifi.woof)
# #or: h.trigger(k.brutus.woofed, k.fifi)
# ###or:
# #try:
# #    h.trigger(k.brutus, k.fifi) #TypeError: ambiguity between woofed and call
# #except:
# #    traceback.print_exc()
#
# print(11)
# k._fifi.call() #=> CALL Fifi; WOOF Fifi 2; WOOF Brutus 2; WOOF Fifi 3
# print("FIFI WOOFS", k._fifi.woofs) #FIFI WOOFS 3
# k._fifi.woofs = 10
# print("FIFI WOOFS", k._fifi.woofs) #FIFI WOOFS 10
# print("K2 FIFI WOOFS", k2._fifi.woofs) #FIFI WOOFS 0
# print(12)
# k._brutus.call() #=> CALL Brutus; WOOF Brutus 3; WOOF Fifi 11
# print(13)
# k2._brutus.call() #=> CALL Brutus; WOOF Brutus 1
# print( "END")