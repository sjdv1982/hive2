from collections import namedtuple


BindInfo = namedtuple("BindInfo", "name is_enabled bind_hive environment_hive")
BindContext = namedtuple("BindContext", "plugins sockets config")
