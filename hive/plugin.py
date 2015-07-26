from .mixins import Plugin, Socket, ConnectSource, Exportable, Callable, Bee, Bindable
from .plugin_policies import SingleRequired, PluginPolicyError
from .manager import get_building_hive, memoize, ContextFactory


class HivePlugin(Plugin, ConnectSource, Bindable, Exportable):

    def __init__(self, func, identifier=None, data_type=None, policy_cls=SingleRequired, auto_connect=False, bound=None):
        assert callable(func) or isinstance(func, Callable), func
        self._bound = bound
        self._func = func

        self.auto_connect = auto_connect
        self.identifier = identifier
        self.data_type = data_type
        self.policy_cls = policy_cls

        if bound:
            self.policy = policy_cls()

    def __repr__(self):
        return "<HivePlugin: {}>".format(self._func)

    def plugin(self):
        return self._func
        
    def _hive_is_connectable_source(self, target):
        if not isinstance(target, Socket):
            raise ValueError("Plugin target must be a subclass of Socket")

        try:
            self.policy.pre_donated()

        except PluginPolicyError as err:
            raise PluginPolicyError("{}\n\tSocket: {}\n\tPlugin: {}".format(err, target, self))

    def _hive_connect_source(self, target):
        self.policy.on_donated()

    @memoize
    def bind(self, run_hive):
        if self._bound:
            return self

        if isinstance(self._func, Bindable):
            func = self._func.bind(run_hive)
            return self.__class__(func, self.identifier, self.data_type, self.policy_cls, self.auto_connect, run_hive)

        else:
            return self

    @memoize
    def export(self):
        # TODO: somehow log the redirection path
        func = self._func
        if isinstance(func, Exportable):
            exported = func.export()
            return self.__class__(exported, self.identifier, self.data_type, policy_cls=self.policy_cls,
                                  bound=self._bound)

        else:
            return self


class HivePluginBee(Plugin, ConnectSource, Exportable):

    def __init__(self, target, identifier=None, data_type=None, policy_cls=SingleRequired, auto_connect=False):
        self._hive_cls = get_building_hive()
        self._target = target

        self.auto_connect = auto_connect
        self.identifier = identifier
        self.data_type = data_type
        self.policy_cls = policy_cls

    def __repr__(self):
        return "<HivePluginBee {})>".format(self._target)

    @memoize
    def getinstance(self, hive_object):
        target = self._target
        if isinstance(target, Bee):
            target = target.getinstance(hive_object)

        return HivePlugin(target, self.identifier, self.data_type, self.policy_cls, self.auto_connect)

    @memoize
    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            exported = target.export()
            return self.__class__(exported, self.identifier, self.data_type, self.policy_cls, self.auto_connect)

        else:
            return self


plugin = ContextFactory("hive.plugin", immediate_mode_cls=HivePlugin, build_mode_cls=HivePluginBee)