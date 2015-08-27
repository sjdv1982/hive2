import hive

from math import sqrt


def declare_vector(args):
    args.operation = hive.parameter("str", "dot", {"dot", "cross", "length"})
    args.dimensions = hive.parameter("int", 3, {2, 3})


def dot2d(self):
    a = self._a
    b = self._b

    return a[0] * b[0] + a[1] * b[1]


def dot3d(self):
    a = self._a
    b = self._b
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def length2d(self):
    a = self._a
    return sqrt(a[0] ** 2 + a[1] ** 2)


def length3d(self):
    a = self._a
    return sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)


def cross3d(self):
    a = self._a
    b = self._b

    x = ((a[2] * b[3]) - (a[3] * b[2]))
    y = ((a[3] * b[1]) - (a[1] * b[3]))
    z = ((a[1] * b[2]) - (a[2] * b[1]))

    return x, y, z


def build_vector(i, ex, args):
    i.a = hive.attribute("vector")
    pull_a = hive.pull_in(i.a)
    ex.a = hive.antenna(pull_a)

    if args.operation in ("dot", "cross"):
        i.b = hive.attribute("vector")
        pull_b = hive.pull_in(i.b)
        ex.b = hive.antenna(pull_b)

        if args.operation == "dot":
            if args.dimensions == 2:
                func = dot2d

            else:
                func = dot3d

        else:
            if args.dimensions != 3:
                raise ValueError("Cross product isn't defined for 2D vectors")

            func = cross3d

    else:
        if args.dimensions == 2:
            func = length2d

        else:
            func = length3d

    i.result = hive.attribute("vector")
    pull_result = hive.pull_out(i.result)
    ex.result = hive.output(pull_result)

    calculate = hive.modifier(func)
    hive.trigger(pull_result, calculate, pretrigger=True)


Vector = hive.hive("Vector", build_vector, declarator=declare_vector)