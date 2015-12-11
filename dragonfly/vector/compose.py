import hive


def compose_modifier(self):
    self.vector.pull()

    self.x = self._vector[0]
    self.y = self._vector[1]
    self.z = self._vector[2]


def build_compose(i, ex, args):
    """Compose a vector from its x, y and z components"""
    i.refresh = hive.modifier(compose_modifier)

    i.vector = hive.attribute("vector")
    i.vector_out = hive.pull_out(i.vector)

    for name in ['x', 'y', 'z']:
        attr = hive.attribute("float")
        setattr(i, name, attr)

        pull_in = hive.pull_in(attr)
        setattr(ex, name, hive.antenna(pull_in))

        hive.trigger(i.vector_out, pull_in, pretrigger=True)

    ex.vector = hive.output(i.vector_out)


Compose = hive.hive("Compose", build_compose)
