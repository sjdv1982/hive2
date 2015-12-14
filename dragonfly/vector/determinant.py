import hive

from math import sqrt


def length_modifier(self):
    vec = self._vec
    self._result = sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)


def build_determinant(i, ex, args):
    """Calculate the determinant (length) of a vector"""
    i.vec = hive.attribute("vector")
    pull_vec = hive.pull_in(i.vec)
    ex.vec = hive.antenna(pull_vec)

    i.result = hive.attribute("float")
    pull_result = hive.pull_out(i.result)
    ex.result = hive.output(pull_result)

    calculate = hive.modifier(length_modifier)
    hive.trigger(pull_result, calculate, pretrigger=True)


Determinant = hive.hive("Determinant", build_determinant)
