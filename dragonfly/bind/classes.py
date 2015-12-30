from collections import namedtuple


BindInfo = namedtuple("BindInfo", "name bind_hive get_environments")
BindContext = namedtuple("BindContext", "plugins sockets config")


def get_bind_bases(bind_infos):
    return tuple((b_i.bind_hive for b_i in bind_infos))


def get_active_bind_environments(bind_infos, meta_args):
    return tuple((env for b_i in bind_infos for env in b_i.get_environments(meta_args)))