import hive
from hive.classes import Method


class HiveInstantiator_:

    def __init__(self, hive_cls):
        self._environment_cls = hive_cls
        self._plugins = {}
        self._sockets = {}

        self.last_created = None

    def set_plugin(self, identifier, plugin):
        self._plugins[identifier] = plugin

    def set_socket(self, identifier, socket):
        self._sockets[identifier] = socket

    @classmethod
    def plugin_setter(cls, identifier):
        def wrapper(self, func):
            self.set_plugin(identifier, func)
        return wrapper

    @classmethod
    def socket_setter(cls, identifier):
        def wrapper(self, func):
            self.set_socket(identifier, func)
        return wrapper

    def instantiate(self):
        environment = self._environment_cls(self._plugins, self._sockets)
        self.last_created = environment.hive


class HiveEnvironment_:

    def __init__(self, plugins, sockets):
        self._plugins = plugins
        self._sockets = sockets

    @classmethod
    def plugin_proxy(cls, identifier):
        def wrapper(self, *args, **kwargs):
            return self._plugins[identifier](*args, **kwargs)
        return wrapper

    @classmethod
    def socket_proxy(cls, identifier):
        def wrapper(self, func):
            self._sockets[identifier](func)
        return wrapper


class Instantiator_:
    pass


def declare_instantiator(meta_args):
    meta_args.cls_import_path = hive.parameter("str")


def build_instantiator(cls, i, ex, args):
    pass




def instantiator(hive_cls, plugins=[], sockets=[]):

    def build_instantiator(cls, i, ex, args):
        for index, (identifier, policy_cls) in enumerate(plugins):
            method = Method(HiveInstantiator_, HiveInstantiator_.plugin_setter(identifier))
            socket = hive.socket(method, identifier=identifier)
            setattr(ex, "socket_{}".format(index), socket)

        for index, (identifier, policy_cls) in enumerate(sockets):
            method = Method(HiveInstantiator_, HiveInstantiator_.socket_setter(identifier))
            plugin = hive.plugin(method, identifier=identifier)
            setattr(ex, "plugin_{}".format(index), plugin)

        i.create = hive.triggerable(cls.instantiate)
        ex.create = hive.entry(i.create)

        ex.last_created = hive.property(cls, "last_created")
        i.last_created_out = hive.pull_out(ex.last_created)
        ex.last_created_out = hive.output(i.last_created_out)

    InstantiatorHive = hive.hive("Instantiator", build_instantiator, HiveInstantiator_)

    def build_environment(cls, i, ex, args):
        for index, (identifier, policy_cls) in enumerate(plugins):
            method = Method(HiveEnvironment_, HiveEnvironment_.plugin_proxy(identifier))
            plugin = hive.plugin(method, identifier=identifier, policy_cls=policy_cls)
            setattr(ex, "plugin_{}".format(index), plugin)

        for index, (identifier, policy_cls) in enumerate(sockets):
            method = Method(HiveEnvironment_, HiveEnvironment_.socket_proxy(identifier))
            socket = hive.socket(method, identifier=identifier, policy_cls=policy_cls)
            setattr(ex, "socket_{}".format(index), socket)

        ex.hive = hive_cls()

    EnvironmentHive = hive.hive("Environment", build_environment, HiveEnvironment_)

    return InstantiatorHive(EnvironmentHive)
