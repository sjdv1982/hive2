def argument_types(**kwargs):
    """Decorate the init function with argument types"""
    def wrapper(init):
        init._hive_arg_types = kwargs
        return init

    return wrapper


def get_argument_types(func):
    try:
        return func._hive_arg_types

    except AttributeError:
        return {}


def argument_options(**kwargs):
    """Decorate the init function with argument options"""
    def wrapper(init):
        init._hive_arg_options = kwargs
        return init

    return wrapper


def get_argument_options(func):
    try:
        return func._hive_arg_options

    except AttributeError:
        return {}
