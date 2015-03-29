from .mixins import ConnectTarget, Plugin, Socket, Callable, Exportable, Bee, Bindable
from .context_factory import ContextFactory
from .socket_policies import SingleRequired
from . import memoize
from . import manager
from . import get_building_hive


class HiveSocket(Socket, ConnectTarget, Bindable, Exportable):

    def __init__(self, func, identifier=None, data_type=None, policy_cls=SingleRequired, bound=False, exported=False):
        assert callable(func) or isinstance(func, Callable), func
        self._bound = bound
        self._exported = exported
        self._func = func

        self.identifier = identifier
        self.data_type = data_type
        self.policy_cls = policy_cls

        if bound:
            self._policy = policy_cls()

    @manager.bind
    def bind(self, run_hive):
        if self._bound: 
            return self

        if isinstance(self._func, Bindable):
            func = self._func.bind(run_hive)
            return self.__class__(func, self.identifier, self.data_type, self.policy_cls, bound=True)

        else:
            return self

    @memoize.method
    def export(self):
        if self._exported:
            return self

        # TODO: somehow log the redirection path
        func = self._func

        if isinstance(func, Exportable):
            exported = func.export()
            return self.__class__(exported, self.identifier, self.data_type, self.policy_cls, bound=self._bound,
                                  exported=True)

        else:
            return self
    
    def _hive_connectable_target(self, source):
        # TODO : nicer error message
        assert isinstance(source, Plugin)

    def _hive_connect_target(self, source):
        plugin = source.plugin()
        self._func(plugin)
    

class HiveSocketBee(Socket, ConnectTarget, Exportable):

    def __init__(self, target, identifier=None, data_type=None, policy_cls=SingleRequired, exported=False):
        self._hive_cls = get_building_hive()
        self._target = target
        self._exported = exported

        self.identifier = identifier
        self.data_type = data_type
        self.policy_cls = policy_cls

    @manager.getinstance
    def getinstance(self, hive_object):
        target = self._target
        if isinstance(target, Bee): 
            target = target.getinstance(hive_object)

        return HiveSocket(target, self.identifier, self.data_type, self.policy_cls)

    @memoize.method
    def export(self):
        if self._exported:
            return self

        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            exported = target.export()

            return self.__class__(exported, self.identifier, self.data_type, self.policy_cls,  exported=True)

        else:
            return self


socket = ContextFactory("hive.socket", immediate_cls=HiveSocket, deferred_cls=HiveSocketBee)