def init_types(**kwargs):
    """Decorate the init function with argument types"""
    def wrapper(init):
        init.types = kwargs
        return init

    return wrapper


def init_options(**kwargs):
    """Decorate the init function with argument options"""
    def wrapper(init):
        init.options = kwargs
        return init

    return wrapper