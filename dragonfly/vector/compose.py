import hive


def compose_modifier(self):
    self.vector = (self.x, self.y, self.z)


def build_compose(i, ex, args):
    """Compose a vector from its x, y and z components"""
    i.compose_vector = hive.modifier(compose_modifier)

    ex.vector = hive.attribute(("vector",))
    i.vector_out = hive.pull_out(ex.vector)

    for name in ['x', 'y', 'z']:
        attr = hive.attribute("float")
        setattr(ex, name, attr)

        pull_in = hive.pull_in(attr)
        setattr(ex, "{}_in".format(name), hive.antenna(pull_in))

        hive.trigger(i.vector_out, pull_in, pretrigger=True)

    hive.trigger(i.vector_out, i.compose_vector, pretrigger=True)
    ex.vector_out = hive.output(i.vector_out)


Compose = hive.hive("Compose", build_compose)
