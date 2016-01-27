import string

import hive


def declare_print(meta_args):
    meta_args.format_string = hive.parameter("str", "{}")


def build_print(i, ex, args, meta_args):
    """Print value to Python stdout.

    Use format string syntax to name pins
    """
    formatter = string.Formatter()
    format_string = meta_args.format_string
    fields = list(formatter.parse(format_string))

    # Single fields can use push in
    if len(fields) == 1:
        # Create IO
        i.value = hive.attribute()
        i.value_in = hive.push_in(i.value)
        ex.value = hive.antenna(i.value_in)

        i.func = hive.modifier(lambda self: print(self._value))
        hive.trigger(i.value_in, i.func)

    else:
        kwarg_fields = []
        indexed_fields = []

        i.pull_inputs = hive.triggerfunc()
        i.trig = hive.triggerable(i.pull_inputs)
        ex.trig = hive.entry(i.trig)

        for index, field in enumerate(fields):
            literal_text = field[1]

            if not literal_text.isidentifier():
                field_name = "field_{}".format(index)
                indexed_fields.append(field_name)

            else:
                field_name = literal_text
                kwarg_fields.append(field_name)

            # Create IO
            attr = hive.attribute()
            setattr(i, field_name, attr)

            in_attr = hive.pull_in(attr)
            setattr(i, "{}_in".format(field_name), in_attr)

            setattr(ex, field_name, hive.antenna(in_attr))
            hive.trigger(i.pull_inputs, in_attr)

        def do_print(self):
            args = [getattr(self, "_{}".format(attr_name)) for attr_name in indexed_fields]
            kwargs = {attr_name: getattr(self, "_{}".format(attr_name)) for attr_name in kwarg_fields}
            print(formatter.format(format_string, *args, **kwargs))

        i.func = hive.modifier(do_print)
        hive.trigger(i.pull_inputs, i.func)


Print = hive.dyna_hive("Print", build_print, declarator=declare_print)
