import hive


def declare_complex(meta_args):
    meta_args.mode = hive.parameter('str', 'compose', options={'compose', 'decompose'})


def build_complex(i, ex, args, meta_args):
    """Compose/decompose complex number"""
    i.value = hive.attribute('complex')
    i.real = hive.attribute('float')
    i.imag = hive.attribute('float')

    if meta_args.mode == 'compose':
        i.pull_imag = hive.pull_in(i.imag)
        i.pull_real = hive.pull_in(i.real)

        ex.real = hive.antenna(i.pull_real)
        ex.imag = hive.antenna(i.pull_imag)

        i.pull_value = hive.pull_out(i.value)
        ex.value = hive.output(i.pull_value)

        def build_value(self):
            self._value = complex(self._real, self._imag)

        i.build_value = hive.modifier(build_value)

        hive.trigger(i.pull_value, i.pull_imag, pretrigger=True)
        hive.trigger(i.pull_imag, i.pull_real)
        hive.trigger(i.pull_real, i.build_value)

    elif meta_args.mode == 'decompose':
        i.pull_imag = hive.pull_out(i.imag)
        i.pull_real = hive.pull_out(i.real)

        ex.real = hive.output(i.pull_real)
        ex.imag = hive.output(i.pull_imag)

        i.pull_value = hive.pull_in(i.value)
        ex.value = hive.antenna(i.pull_value)

        def build_value(self):
            value = self._value
            self._real = value.real
            self._imag = value.imag

        i.build_value = hive.modifier(build_value)

        hive.trigger(i.pull_imag, i.pull_value, pretrigger=True)
        hive.trigger(i.pull_real, i.pull_value, pretrigger=True)
        hive.trigger(i.pull_value, i.build_value)


Complex = hive.dyna_hive("Complex", build_complex, declarator=declare_complex)