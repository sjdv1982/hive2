import hive

from collections import namedtuple

from ..bind import BindContext
from ..event import bind_info as event_bind_info


bind_infos = (event_bind_info,)


class BindEnvironmentClass:

    def __init__(self, context, bind_id):
        self.bind_id = bind_id

    def get_bind_id(self):
        return self.bind_id


def declare_build_environment(meta_args):
    meta_args.bind_configuration = hive.parameter("dict")


def build_bind_environment(cls, i, ex, args, meta_args):
    from gui.utils import import_from_path
    ex.hive = import_from_path(meta_args.bind_configuration.cls_import_path)()
    ex.get_bind_id = hive.plugin(cls.get_bind_id, identifier=("bind", "get_identifier"))


class InstantiatorCls:

    def __init__(self):
        self.bind_meta_class = None

        self._plugin_getters = []
        self._socket_getters = []
        self._config_getters = []

        self._context = None

        self._hive = hive.get_run_hive()

        self.last_created = None
        self.bind_id = None

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

        # If this is build at build time, then it won't perform matchmaking
        bind_class = self.bind_meta_class(self._hive._hive_object._hive_meta_args_frozen)
        self.last_created = bind_class(context, bind_id=self.bind_id)


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

    ex.create = hive.entry(i.do_instantiate)
    ex.last_created = hive.property(cls, "last_created", "object")

    ex.add_get_plugins = hive.socket(cls.add_get_plugins, identifier=("bind", "get_plugins"),
                                     policy=hive.MultipleOptional)
    ex.add_get_sockets = hive.socket(cls.add_get_plugins, identifier=("bind", "get_sockets"),
                                     policy=hive.MultipleOptional)
    ex.add_get_config = hive.socket(cls.add_get_config, identifier=("bind", "get_config"), policy=hive.MultipleOptional)


Instantiator = hive.dyna_hive("Instantiator", builder=build_instantiator, declarator=declare_instantiator,
                              cls=InstantiatorCls, bases=tuple(i.bind_hive for i in bind_infos))
