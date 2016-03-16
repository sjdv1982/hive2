from collections import namedtuple


BindInfo = namedtuple("BindInfo", "name bind_hive get_environment")
BindContext = namedtuple("BindContext", "plugins config")


def get_bind_bases(bind_infos):
    """Return tuple of base classes for a bind-hive from tuple of required bind infos"""
    return tuple((b_i.bind_hive for b_i in bind_infos))


def get_active_bind_environments(bind_infos, meta_args):
    """Return tuple of base classes for bind-environments from tuple of required bind infos and meta args wrapper"""
    environments = []
    for info in bind_infos:
        environment = info.get_environment(meta_args)
        if environment:
            environments.append(environment)

    return tuple(environments)