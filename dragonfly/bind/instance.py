from collections import OrderedDict

import hive
from dragonfly.bind import BindContext


class FrozenDict:
    """Immutable, ordered dictionary object"""

    def __init__(self, data):
        if not isinstance(data, OrderedDict):
            raise TypeError("data must be instance of OrderedDict")

        self._dict = dict(data)
        self._items = tuple(data.items())

        if self._items:
            self._keys, self._values = zip(*self._items)

        else:
            self._keys = self._values = ()

        self._hash = hash((self._keys, self._values))

    def __getitem__(self, item):
        return self._dict[item]

    def __hash__(self):
        return self._hash

    def keys(self):
        return self._keys

    def items(self):
        return self._items

    def values(self):
        return self._values

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._keys)


class BindEnvironmentClass:

    def __init__(self, context, bind_id):
        self.bind_id = bind_id

        self._alive = True
        self._closers = []

    def add_closer(self, closer):
        self._closers.append(closer)

    def close(self):
        if not self._alive:
            raise RuntimeError("Hive already closed")

        for closer in self._closers:
            closer()

        self._closers.clear()
        self._alive = False

    def get_bind_id(self):
        return self.bind_id


def declare_build_environment(meta_args):
    meta_args.bind_meta_args = hive.parameter("object")
    meta_args.import_path = hive.parameter("str")


def build_bind_environment(cls, i, ex, args, meta_args):
    """Provides sockets and plugins to new embedded hive instance"""
    ex.hive = meta_args.hive_cls()
    ex.get_bind_id = hive.plugin(cls.get_bind_id, identifier=("bind", "get_identifier"))
    ex.get_closers = hive.socket(cls.add_closer, identifier=("bind", "add_closer"), policy=hive.MultipleOptional)

    i.do_close = hive.triggerable(cls.close)
    ex.close = hive.entry(i.do_close)


class InstantiatorCls:

    def __init__(self):
        self._plugin_getters = []
        self._socket_getters = []
        self._config_getters = []

        self._plugins = None
        self._sockets = None

        self._hive = hive.get_run_hive()

        self.last_created = None
        self.bind_meta_class = None

        # Runtime attributes
        self.bind_id = None
        self.hive_class = None

    def _create_context(self):
        if self._plugins is None:
            self._plugins = plugins = {}
            for getter in self._plugin_getters:
                plugins.update(getter())

        if self._sockets is None:
            self._sockets = sockets = {}
            for getter in self._socket_getters:
                sockets.update(getter())

        config = {}
        for getter in self._config_getters:
            config.update(getter())

        return BindContext(self._plugins, self._sockets, config)

    def add_get_plugins(self, get_plugins):
        """Add plugin context source

        :param get_plugins: plugins context getter
        """
        self._plugin_getters.append(get_plugins)

    def add_get_sockets(self, get_sockets):
        """Add socket context source

        :param get_sockets: sockets context getter
        """
        self._socket_getters.append(get_sockets)

    def add_get_config(self, get_config):
        """Add config context source

        :param get_config: config context getter
        """
        self._config_getters.append(get_config)

    def instantiate(self):
        context = self._create_context()

        # Pull a new bind ID and args dict
        self._hive.bind_id()
        self._hive.hive_class()

        bind_meta_args = self._hive._hive_object._hive_meta_args_frozen
        bind_class = self.bind_meta_class(bind_meta_args=bind_meta_args, hive_class=self.hive_class)

        self.last_created = bind_class(context, bind_id=self.bind_id)


def build_instantiator(cls, i, ex, args, meta_args):
    """Instantiates a Hive class at runtime"""
    # If this is built now, then it won't perform matchmaking, so use meta hive
    bind_meta_class = hive.meta_hive("BindEnvironment", build_bind_environment, declare_build_environment,
                                     cls=BindEnvironmentClass)
    i.bind_meta_class.start_value = hive.property(cls, "bind_meta_class", "object", bind_meta_class)

    i.do_instantiate = hive.triggerable(cls.instantiate)

    # Get bind ID
    i.bind_id = hive.property(cls, "bind_id", ("str", "id"))
    i.pull_bind_id = hive.pull_in(i.bind_id)
    ex.bind_id = hive.antenna(i.pull_bind_id)

    # Get import path
    i.hive_class = hive.property(cls, "hive_class", "class")
    i.pull_hive_class = hive.pull_in(i.hive_class)
    ex.hive_class = hive.antenna(i.pull_hive_class)

    ex.create = hive.entry(i.do_instantiate)

    ex.last_created_hive = hive.property(cls, "last_created", "object")
    i.pull_last_created = hive.pull_out(ex.last_created_hive)
    ex.last_created = hive.output(i.pull_last_created)

    ex.add_get_plugins = hive.socket(cls.add_get_plugins, identifier=("bind", "get_plugins"),
                                     policy=hive.MultipleOptional)
    ex.add_get_sockets = hive.socket(cls.add_get_plugins, identifier=("bind", "get_sockets"),
                                     policy=hive.MultipleOptional)
    ex.add_get_config = hive.socket(cls.add_get_config, identifier=("bind", "get_config"), policy=hive.MultipleOptional)


Instantiator = hive.hive("Instantiator", builder=build_instantiator, cls=InstantiatorCls)
