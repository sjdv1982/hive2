import hive


def decompose_modifier(self):
    self._vector.pull()

    self._x = self._vector[0]
    self._y = self._vector[1]
    self._z = self._vector[2]


def build_decompose(i, ex, args):
    """Decompose a eulerr into its x, y and z components"""
    i.refresh = hive.modifier(decompose_modifier)

    for name in ['x', 'y', 'z']:
        attr = hive.attribute("euler")
        setattr(i, name, attr)

        pull_out = hive.pull_out(attr)
        setattr(ex, name, hive.output(pull_out))

        hive.trigger(pull_out, i.refresh, pretrigger=True)

    i.eulerr = hive.attribute("eulerr")
    i.pull_vector = hive.pull_in(i.eulerr)
    ex.eulerr = hive.antenna(i.pull_vector)


Decompose = hive.hive("Decompose", build_decompose)
