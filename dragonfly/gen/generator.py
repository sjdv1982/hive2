import hive


class _GeneratorCls:

    def __init__(self):
        self.generator = None
        self.generator_func = None

    def pull_out(self):
        generator = self.generator
        if generator is None:
            self.generator = generator = self.generator_func()

        return next(generator)


def build_generator(cls, i, ex, args):
    """Iterate over generator object, output new value when pulled"""
    args.generator = hive.parameter(("object", "generator"))
    ex.generator = hive.property(cls, "generator_func", ("object", "generator"), args.generator)
    i.pull_value = hive.pull_out(cls.pull_out)
    ex.value = hive.output(i.pull_value)


Generator = hive.hive("Generator", build_generator, cls=_GeneratorCls)
