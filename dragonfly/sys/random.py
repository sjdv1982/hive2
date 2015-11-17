import hive

from random import Random as RNG


class _RandomCls:

    @hive.argument_types(seed="float")
    def __init__(self, seed=None):
        self.rng = RNG()
        self.rng.seed(seed)

        self.randint_min = None
        self.randint_max = None

        self.randrange_min = None
        self.randrange_max = None

    def set_seed(self, seed):
        self.rng.seed(seed)

    def get_rand(self):
        return self.rng.random()

    def get_bool(self):
        return self.get_rand() >= 0.5

    def get_randint(self):
        return self.rng.randint(self.randint_min, self.randint_max)

    def get_randrange(self):
        return self.rng.randrange(self.randrange_min, self.randrange_max)


def build_random(cls, i, ex, args):
    """HIVE interface to Python random module"""
    i.seed_in = hive.push_in(cls.set_seed)
    ex.seed_in = hive.antenna(i.seed_in)

    i.rand_out = hive.pull_out(cls.get_rand)
    ex.rand_out = hive.output(i.rand_out)

    i.bool_out = hive.pull_out(cls.get_bool)
    ex.bool_out = hive.output(i.bool_out)

    # Randint
    i.randint_min = hive.property(cls, "randint_min", "int")
    i.randint_max = hive.property(cls, "randint_max", "int")

    i.randint_min_in = hive.pull_in(i.randint_min)
    i.randint_max_in = hive.pull_in(i.randint_max)

    ex.int_min_in = hive.antenna(i.randint_min_in)
    ex.int_max_in = hive.antenna(i.randint_max_in)

    i.randint_out = hive.pull_out(cls.get_randint)
    ex.int_out = hive.output(i.randint_out)

    hive.trigger(i.randint_out, i.randint_max_in, pretrigger=True)
    hive.trigger(i.randint_out, i.randint_min_in, pretrigger=True)

    # Randrange
    i.randrange_min = hive.property(cls, "randrange_min", "float")
    i.randrange_max = hive.property(cls, "randrange_max", "float")

    i.randrange_min_in = hive.pull_in(i.randrange_min)
    i.randrange_max_in = hive.pull_in(i.randrange_max)

    ex.range_min_in = hive.antenna(i.randrange_min_in)
    ex.range_max_in = hive.antenna(i.randrange_max_in)

    i.randrange_out = hive.pull_out(cls.get_randrange)
    ex.range_out = hive.output(i.randrange_out)

    hive.trigger(i.randrange_out, i.randrange_max_in, pretrigger=True)
    hive.trigger(i.randrange_out, i.randrange_min_in, pretrigger=True)

Random = hive.hive("Random", build_random, cls=_RandomCls)