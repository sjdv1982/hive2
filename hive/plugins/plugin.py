from .policies import SingleOptional, PluginPolicyError
from ..manager import get_building_hive, memoize, ContextFactory
from ..mixins import Plugin, Socket, ConnectSource, Exportable, Callable, Bee, Bindable, Closable
from ..tuple_type import tuple_type


class HivePlugin(Plugin, ConnectSource, Bindable, Exportable, Closable):

    def __init__(self, func, data_type=None, run_hive=None, _policy_cls=SingleOptional):
        assert callable(func) or isinstance(func, Callable), func
        self._run_hive = run_hive
        self._func = func

        self.data_type = tuple_type(data_type)
        self._policy_cls = _policy_cls

        if run_hive:
            self.policy = _policy_cls()

        else:
            self.policy = None

    def __repr__(self):
        return "<Plugin: {}>".format(self._func)

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
        if self._run_hive:
            return self

        if isinstance(self._func, Bindable):
            func = self._func.bind(run_hive)

        else:
            func = self._func

        return self.__class__(func, self.data_type, run_hive, _policy_cls=self._policy_cls)

    def close(self):
        if not self.policy.is_satisfied:
            raise ValueError("Policy not satisfied for {}!".format(self._hive_bee_name), self.policy)

    @memoize
    def export(self):
        # TODO: somehow log the redirection path
        func = self._func
        if isinstance(func, Exportable):
            exported = func.export()
            return self.__class__(exported, self.data_type, self._run_hive, _policy_cls=self._policy_cls)

        else:
            return self


class HivePluginBee(Plugin, ConnectSource, Exportable):

    def __init__(self, target, identifier=None, data_type=None, policy_cls=SingleOptional, export_to_parent=False):
        self._hive_object_cls = get_building_hive()
        self._target = target

        self.export_to_parent = export_to_parent
        self.identifier = identifier
        self.data_type = tuple_type(data_type)

        self.policy_cls = policy_cls

    def __repr__(self):
        return "<Plugin: {}>".format(self._target)

    @memoize
    def getinstance(self, hive_object):
        target = self._target
        if isinstance(target, Bee):
            target = target.getinstance(hive_object)

        return HivePlugin(target, self.data_type, _policy_cls=self.policy_cls)

    @memoize
    def export(self):
        # TODO: somehow log the redirection path
        target = self._target

        if isinstance(target, Exportable):
            exported = target.export()
            return self.__class__(exported, self.identifier, self.data_type, self.policy_cls, self.export_to_parent)

        else:
            return self


plugin = ContextFactory("hive.plugin", immediate_mode_cls=HivePlugin, build_mode_cls=HivePluginBee)
