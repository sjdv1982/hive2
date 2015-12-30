import hive

from .classes import BindContext


class BindEnvironmentClass:

    def __init__(self, context):
        self._on_stopped = []
        self._on_started = []

        self.state = 'init'

    def add_on_started(self, on_started):
        self._on_started.append(on_started)

    def add_on_stopped(self, on_stopped):
        self._on_stopped.append(on_stopped)

    def start(self):
        if self.state != 'init':
            raise RuntimeError("Hive is already running")

        self.state = 'running'

        for callback in self._on_started:
            callback()

    def stop(self):
        if self.state != 'running':
            raise RuntimeError("Hive is already stopped")

        self.state = 'stopped'

        for callback in self._on_stopped:
            callback()


def declare_build_environment(meta_args):
    meta_args.bind_meta_args = hive.parameter("object")
    meta_args.hive_class = hive.parameter("class")


def build_bind_environment(cls, i, ex, args, meta_args):
    """Provides sockets and plugins to new embedded hive instance"""
    ex.hive = meta_args.hive_class()

    # Startup / End callback
    ex.get_on_started = hive.socket(cls.add_on_started, identifier=("on_started",), policy=hive.MultipleOptional)
    ex.get_on_stopped = hive.socket(cls.add_on_stopped, identifier=("on_stopped",), policy=hive.MultipleOptional)

    i.on_started = hive.triggerable(cls.start)
    i.on_stopped = hive.triggerable(cls.stop)

    ex.on_started = hive.entry(i.on_started)
    ex.on_stopped = hive.entry(i.on_stopped)

    i.state = hive.property(cls, 'state', 'str')
    i.pull_state = hive.pull_out(i.state)
    ex.state = hive.output(i.pull_state)

# TODO (s)
# Close should be subscribed by event to send stop event
# Stop is local, quit is global
# Make panels scrollable!
# When send start / stop events? Who? how deal with binding?
# Add scheduling?


class InstantiatorCls:

    def __init__(self):
        self._plugin_getters = []
        self._socket_getters = []
        self._config_getters = []

        self._plugins = None
        self._sockets = None

        self._hive = hive.get_run_hive()
        self._active_hives = []

        self._bind_class_creation_callbacks = []

        self.last_created = None
        self.bind_meta_class = None

        # Runtime attributes
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

    def add_on_created(self, on_created):
        self._bind_class_creation_callbacks.append(on_created)

    def forget_hive(self, child_hive):
        """Forget child hive when it is stopped"""
        self._active_hives.remove(child_hive)

    def on_stopped(self):
        """Stop all child hives if instantiator is stopped"""
        for child_hive in self._active_hives[:]:
            child_hive.on_stopped()

    def instantiate(self):
        context = self._create_context()

        # Pull a new bind ID and args dict
        self._hive.hive_class()

        bind_meta_args = self._hive._hive_object._hive_meta_args_frozen
        bind_class = self.bind_meta_class(bind_meta_args=bind_meta_args, hive_class=self.hive_class)

        self.last_created = environment_hive = bind_class(context)

        # Notify bind classes of new hive instance (environment_hive)
        for callback in self._bind_class_creation_callbacks:
            callback(environment_hive)

        # Deregister hive if it is stopped
        on_stopped = hive.plugin(lambda: self.forget_hive(environment_hive))
        hive.connect(on_stopped, environment_hive.get_on_stopped)

        environment_hive.on_started()
        self._active_hives.append(environment_hive)


def declare_instantiator(meta_args):
    meta_args.bind_process = hive.parameter("str", 'dependent', {'dependent', 'independent'})


def build_instantiator(cls, i, ex, args, meta_args):
    """Instantiates a Hive class at runtime"""
    # If this is built now, then it won't perform matchmaking, so use meta hive
    bind_meta_class = hive.meta_hive("BindEnvironment", build_bind_environment, declare_build_environment,
                                     cls=BindEnvironmentClass)
    i.bind_meta_class = hive.property(cls, "bind_meta_class", "object", bind_meta_class)

    i.do_instantiate = hive.triggerable(cls.instantiate)

    i.hive_class = hive.property(cls, "hive_class", "class")
    i.pull_hive_class = hive.pull_in(i.hive_class)
    ex.hive_class = hive.antenna(i.pull_hive_class)

    ex.create = hive.entry(i.do_instantiate)

    ex.last_created_hive = hive.property(cls, "last_created", "object")
    i.pull_last_created = hive.pull_out(ex.last_created_hive)
    ex.last_created = hive.output(i.pull_last_created)

    # Bind class plugin
    ex.on_created = hive.socket(cls.add_on_created, identifier=("bind", "on_created"), policy=hive.MultipleOptional)

    ex.add_get_plugins = hive.socket(cls.add_get_plugins, identifier=("bind", "get_plugins"),
                                     policy=hive.MultipleOptional)
    ex.add_get_sockets = hive.socket(cls.add_get_plugins, identifier=("bind", "get_sockets"),
                                     policy=hive.MultipleOptional)
    ex.add_get_config = hive.socket(cls.add_get_config, identifier=("bind", "get_config"), policy=hive.MultipleOptional)

    # Bind instantiator
    if meta_args.bind_process == 'dependent':
        # Add startup and stop callbacks
        ex.on_stopped = hive.plugin(cls.on_stopped, identifier=("on_stopped",))

Instantiator = hive.dyna_hive("Instantiator", build_instantiator, declare_instantiator, cls=InstantiatorCls)
