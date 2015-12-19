from collections import OrderedDict

import hive
from ..bind import BindContext
from ..event import bind_info as event_bind_info


bind_infos = (event_bind_info,)


class FrozenDict:

    def __init__(self, data):
        self._dict = OrderedDict()

        for key in sorted(data.keys()):
            self._dict[key] = data[key]

    def __getitem__(self, item):
        return self._dict[item]

    def __hash__(self):
        return hash(tuple(self._dict.items()))

    def keys(self):
        return self._dict.keys()

    def items(self):
        return self._dict.items()

    def values(self):
        return self._dict.values()

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)


class BindEnvironmentClass:

    def __init__(self, context, bind_id):
        self.bind_id = bind_id

    def get_bind_id(self):
        return self.bind_id


def declare_build_environment(meta_args):
    meta_args.bind_configuration = hive.parameter("object")
    meta_args.args = hive.parameter("frozen_dict")


def build_bind_environment(cls, i, ex, args, meta_args):
    from gui.utils import import_from_path

    ex.hive = import_from_path(meta_args.bind_configuration.cls_import_path)(**meta_args.args)
    ex.get_bind_id = hive.plugin(cls.get_bind_id, identifier=("bind", "get_identifier"))


class InstantiatorCls:

    def __init__(self):
        self._plugin_getters = []
        self._socket_getters = []
        self._config_getters = []

        self._context = None

        self._hive = hive.get_run_hive()

        self.last_created = None
        self.bind_meta_class = None
        self.bind_id = None
        self.args = None

    def _get_context(self):
        plugins = {}
        for getter in self._plugin_getters:
            plugins.update(getter())

        sockets = {}
        for getter in self._socket_getters:
            sockets.update(getter())

        config = {}
        for getter in self._config_getters:
            config.update(getter())

        return BindContext(plugins, sockets, config)

    def add_get_plugins(self, get_plugins):
        self._plugin_getters.append(get_plugins)

    def add_get_sockets(self, get_sockets):
        self._socket_getters.append(get_sockets)

    def add_get_config(self, get_config):
        self._config_getters.append(get_config)

    def instantiate(self):
        if self._context is None:
            self._context = self._get_context()

        context = self._context

        self._hive.bind_id()
        self._hive.args()

        # If this is build at build time, then it won't perform matchmaking
        bind_configuration = self._hive._hive_object._hive_meta_args_frozen
        args = FrozenDict(self.args)
        bind_class = self.bind_meta_class(bind_configuration=bind_configuration, args=args)

        self.last_created = bind_class(context, bind_id=self.bind_id).hive


def declare_instantiator(meta_args):
    meta_args.cls_import_path = hive.parameter("str")


def build_instantiator(cls, i, ex, args, meta_args):
    """Instantiates a Hive class at runtime"""
    bind_bases = tuple((b_i.environment_hive for b_i in bind_infos if b_i.is_enabled(meta_args)))
    bind_meta_class = hive.meta_hive("BindEnvironment", build_bind_environment, declare_build_environment,
                                     cls=BindEnvironmentClass, bases=tuple(bind_bases))

    i.bind_meta_class = hive.property(cls, "bind_meta_class", "object", bind_meta_class)

    i.do_instantiate = hive.triggerable(cls.instantiate)

    i.bind_id = hive.property(cls, "bind_id", ("str", "id"))
    i.pull_bind_id = hive.pull_in(i.bind_id)
    ex.bind_id = hive.antenna(i.pull_bind_id)

    i.args = hive.property(cls, "args", "dict")
    i.pull_args = hive.pull_in(i.args)
    ex.args = hive.antenna(i.pull_args)

    ex.create = hive.entry(i.do_instantiate)
    ex.last_created = hive.property(cls, "last_created", "object")

    ex.add_get_plugins = hive.socket(cls.add_get_plugins, identifier=("bind", "get_plugins"),
                                     policy=hive.MultipleOptional)
    ex.add_get_sockets = hive.socket(cls.add_get_plugins, identifier=("bind", "get_sockets"),
                                     policy=hive.MultipleOptional)
    ex.add_get_config = hive.socket(cls.add_get_config, identifier=("bind", "get_config"), policy=hive.MultipleOptional)


Instantiator = hive.dyna_hive("Instantiator", builder=build_instantiator, declarator=declare_instantiator,
                              cls=InstantiatorCls, bases=tuple(i.bind_hive for i in bind_infos))
