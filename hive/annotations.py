def types(**kwargs):
    """Decorate function with argument types"""
    def wrapper(func):
        for arg_name, data_type in kwargs.items():
            if not isinstance(data_type, str):
                raise TypeError("Expected string for data type, received {}='{}'"
                                .format(arg_name, data_type))

        func._hive_arg_types = kwargs
        return func

    return wrapper


def get_argument_types(func):
    try:
        return func._hive_arg_types

    except AttributeError:
        return {}
    

def return_type(type_):
    """Decorate function with argument return type"""
    if not isinstance(type_, str):
        raise TypeError("Expected string for return type, received '{}'".format(type_))

    def wrapper(func):
        func._hive_return_type = type_
        return func
    
    return wrapper


def get_return_type(func):
    try:
        return func._hive_return_type

    except AttributeError:
        return None


def options(**kwargs):
    """Decorate function with argument options"""
    def wrapper(func):
        func._hive_arg_options = kwargs
        return func

    return wrapper


def get_argument_options(func):
    try:
        return func._hive_arg_options

    except AttributeError:
        return {}


def update_wrapper(wrapper, func):
    for attr_name in "_hive_arg_types", "_hive_return_type", "_hive_arg_options":
        if hasattr(func, attr_name):
            setattr(wrapper, attr_name, getattr(func, attr_name))
