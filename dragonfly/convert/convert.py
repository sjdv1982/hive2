import hive

from collections import OrderedDict


_type_map = OrderedDict((("str", str), ("bool", bool), ("int", int), ("float", float), ("dict", dict), ("list", list),
                         ("set", set), ("tuple", tuple)))


def declare_convert(meta_args):
    meta_args.from_data_type = hive.parameter("tuple", ("int",))
    meta_args.to_data_type = hive.parameter("tuple", ("int",))
    meta_args.mode = hive.parameter("str", "pull", {"push", "pull"})
    meta_args.conversion = hive.parameter("str", "duck", {"duck", "cast"})


def build_convert(i, ex, args, meta_args):
    # Setup attributes
    if meta_args.conversion == "cast":
        i.value_in = hive.attribute(meta_args.from_data_type)
        i.value_out = hive.attribute(meta_args.to_data_type)

    # Don't need second attribute if not modifying value
    else:
        i.value_in = hive.attribute(meta_args.from_data_type)
        i.value_out = i.value_in

    # For push in, push out
    if meta_args.mode == "push":
        i.ppin = hive.push_in(i.value_in)
        i.ppout = hive.push_out(i.value_out)

        hive.trigger(i.ppin, i.ppout)

    else:
        i.ppin = hive.pull_in(i.value_in)
        i.ppout = hive.pull_out(i.value_out)

        hive.trigger(i.ppout, i.ppin, pretrigger=True)

    # For casting (explicit conversion)
    if meta_args.conversion == "cast":
        to_base_type_name = meta_args.to_data_type[0]

        if to_base_type_name == "object":
            def converter(self):
                self._value_out = self._value_in

        else:
            value_cls = _type_map[to_base_type_name]

            def converter(self):
                self._value_out = value_cls(self._value_in)

        i.do_conversion = hive.modifier(converter)
        hive.trigger(i.ppout, i.do_conversion, pretrigger=True)

    ex.value_in = hive.antenna(i.ppin)
    ex.value_out = hive.output(i.ppout)


Convert = hive.dyna_hive("Convert", builder=build_convert, declarator=declare_convert)
