import hive

from hive.compatability import next


def next_modifier(self):
    generator = self._generator

    if generator is None:
        self._pull_generator()
        if generator is self._generator:
            raise StopIteration("Could not pull a new generator")

        generator = self._generator

    try:
        self._result = next(generator)

    except StopIteration:
        self._generator = None
        next_modifier(self)


def declare_next(meta_args):
    meta_args.data_type = hive.parameter("str", "int")


def build_next(i, ex, args, meta_args):
    """Iterate over generator object, output new value when pulled"""
    i.generator = hive.attribute()
    i.generator_in = hive.pull_in(i.generator)
    ex.generator = hive.antenna(i.generator_in)

    i.pull_generator = hive.triggerfunc()
    hive.trigger(i.pull_generator, i.generator_in)

    i.result = hive.attribute(meta_args.data_type)
    i.pull_value = hive.pull_out(i.result)
    ex.value = hive.output(i.pull_value)

    i.do_next = hive.modifier(next_modifier)

    hive.trigger(i.pull_value, i.do_next, pretrigger=True)


Next = hive.dyna_hive("Next", build_next, declarator=declare_next)
