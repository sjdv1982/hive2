from inspect import signature

import hive


def create_func(expression):
    prev_namespace = dict(locals())
    exec(expression, prev_namespace)
    new_keys = (k for k in locals() if k not in prev_namespace)

    for key, value in dict(locals()).items():
        if key in prev_namespace:
            continue

        if callable(value):
            return value

    raise ValueError


def f(x:'int') -> 'str':
    pass


def create_wrapper_func(expression, param_names):
    declaration = """
def func(self):
    {}

    {}
    """

    body = expression.replace("\n", "\n    ")
    if not body:
        body = "pass"

    param_declarations = ["{0} = self._{0}".format(name) for name in param_names]
    param_body = "\n\t".join(param_declarations)
    declaration_string = declaration.format(param_body, body)
    exec(declaration_string, locals(), globals())

    return func


def declare_call(meta_args):
    meta_args.declaration = hive.parameter(("str", "code"))


def build_call(i, ex, args, meta_args):
    func = create_func(meta_args.declaration)
    spec = signature(func)

    for name, parameter in spec.parameters.items():
        if parameter.annotation is parameter.empty:
            raise ValueError("Expected annotation for parameter '{}'".format(name))

        attr = hive.attribute(parameter.annotation)
        pull_in = hive.pull_in(attr)
        antenna = hive.antenna(pull_in)

        setattr(i, name, attr)
        setattr(i, "pull_{}".format(name), pull_in)
        setattr(ex, name, antenna)

    wrapped_func = create_wrapper_func(meta_args.declaration, spec.parameters)
    i.modifier = hive.modifier(wrapped_func)

    return_type = spec.return_annotation

    if return_type is spec.empty:
        raise ValueError("Expected annotation for return parameter")

    i.result = hive.attribute(return_type)
    i.pull_result = hive.pull_out(i.result)
    ex.result = hive.output(i.pull_result)

    hive.trigger(i.pull_result, i.modifier, pretrigger=True)


Call = hive.dyna_hive("Call", build_call, declare_call)