from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive
import debug

# Enable debugging
debug.enabled = True


def build_hive2(i, ex, args):
    i.variable = hive.variable()
    i.output = hive.pull_out(i.variable)
    ex.output = hive.output(i.output)

Hive2 = hive.hive("Hive2", build_hive2)


def build_hive1(i, ex, args):
    i.inp = hive.variable()
    i.pinp = hive.pull_in(i.inp)
    ex.input = hive.antenna(i.pinp)

    i.hive2 = Hive2()
    hive.connect(i.hive2, i.pinp)


Hive1 = hive.hive("Hive1", build_hive1)
hive1 = Hive1()

hive1._hive2._variable = 12
hive1.input.pull()

print(hive1._inp)
print(debug.report.stack)

import debug
ostack = debug.report.stack.copy()
debug.report.decode_and_fill_stack(debug.report.encode_and_clear_stack())

print(debug.report.stack, ostack)