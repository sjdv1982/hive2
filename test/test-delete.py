from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


def build_hive1(i, ex, args):
    i.inp = hive.variable()
    i.pinp = hive.push_in(i.inp)
    ex.input = hive.antenna(i.pinp)


Hive1 = hive.hive("Hive1", build_hive1)


def build_myhive(i, ex, args):
    i.output = hive.variable()
    i.push_output = hive.push_out(i.output)
    i.hive1 = Hive1()

    hive.connect(i.push_output, i.hive1.input)

    i.do = hive.triggerfunc()
    hive.trigger(i.do, i.push_output)

    i.m = hive.modifier(lambda h: print("Triggered"))
    hive.trigger(i.hive1.input, i.m)

    i.hive1 = None
    print(dir(i))

    ex.do = hive.hook(i.do)


MyHive = hive.hive("MyHive", build_myhive)


# Create runtime hive instances
my_hive = MyHive()

my_hive.do()


def declare_myhive(args):
    args.depth = hive.parameter("int", 3)
    args.initial_depth = hive.parameter("int")


def build_myhive(i, ex, args):
    initial_depth = args.initial_depth
    if initial_depth is None:
        initial_depth = args.depth

    if args.depth:
        ex.hive = MyHive(args.depth - 1, initial_depth)

    else:
        ex.i_attr = hive.attribute()
        i.push = hive.push_in(ex.i_attr)
        ex.input = hive.antenna(i.push)
        i.modifier = hive.modifier(lambda h: print("TRIGGERED", h.i_attr))
        hive.trigger(i.push, i.modifier)

    if initial_depth == args.depth:
        h = ex.hive
        while h:
            try:
                h = h.hive
            except AttributeError:
                break

        ex.attr = hive.attribute()
        i.push = hive.push_out(ex.attr)
        hive.connect(i.push, h.input)
        ex.value = hive.output(i.push)

MyHive = hive.hive("MyHive", build_myhive, declarator=declare_myhive)
h = MyHive()

h.attr = 12
h.value.push()