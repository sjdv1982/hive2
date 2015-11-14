import hive


def declare_call(meta_args):
    meta_args.result_type = hive.parameter("tuple", ("int",))


def modifier(self):
    kwargs = {} # TODO
    self._result = self._callable(**kwargs)


def build_call(i, ex, args, meta_args):
    """Call callable object with provided inputs and output result"""
    i.callable = hive.attribute(("object", "callable"))
    i.pull_callable = hive.pull_in(i.callable)
    ex.callable = hive.antenna(i.pull_callable)
    i.modifier = hive.modifier(modifier)

    i.result = hive.attribute(meta_args.result_type)
    i.pull_result = hive.pull_out(i.result)
    ex.result = hive.output(i.pull_result)

    hive.trigger(i.pull_result, i.pull_callable, pretrigger=True)
    hive.trigger(i.pull_result, i.modifier, pretrigger=True)

    # TODO, kwargs as pins


Call = hive.dyna_hive("Call", build_call, declarator=declare_call)
