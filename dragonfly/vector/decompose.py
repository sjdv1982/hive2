import hive


def decompose_modifier(self):
    self.vector.pull()

    self.x = self._vector[0]
    self.y = self._vector[1]
    self.z = self._vector[2]


def build_decompose(i, ex, args):
    """Decompose a vector into its x, y and z components"""
    i.refresh = hive.modifier(decompose_modifier)

    for name in ['x', 'y', 'z']:
        attr = hive.attribute("float")
        setattr(i, name, attr)

        pull_out = hive.pull_out(attr)
        setattr(ex, name, hive.output(pull_out))

        hive.trigger(pull_out, i.refresh, pretrigger=True)

    i.vector = hive.attribute("vector")
    i.vector_in = hive.pull_in(i.vector)
    ex.vector = hive.antenna(i.vector_in)


Decompose = hive.hive("Decompose", build_decompose)