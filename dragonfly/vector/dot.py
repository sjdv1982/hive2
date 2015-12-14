import hive


def dot_modifier(self):
    a = self._a
    b = self._b
    self._result = (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def build_dot(i, ex, args):
    """Calculate the dot product between two vectors"""
    i.a = hive.attribute("vector")
    i.b = hive.attribute("vector")

    pull_a = hive.pull_in(i.a)
    pull_b = hive.pull_in(i.b)

    ex.a = hive.antenna(pull_a)
    ex.b = hive.antenna(pull_b)

    i.result = hive.attribute("float")
    pull_result = hive.pull_out(i.result)
    ex.result = hive.output(pull_result)

    calculate = hive.modifier(dot_modifier)
    hive.trigger(pull_result, calculate, pretrigger=True)


Dot = hive.hive("Dot", build_dot)
