from .mixins import ConnectTarget, Plugin, Socket, Callable, Exportable, Bee, Bindable
from .context_factory import ContextFactory
from . import manager
from . import get_building_hive


class HiveSocket(Socket, ConnectTarget, Bindable, Exportable):

    def __init__(self, func, bound=False):
        assert callable(func) or isinstance(func, Callable), func
        self._func = func
        self._bound = bound

    @manager.bind
    def bind(self, run_hive):
        if self._bound: 
            return self

        if isinstance(self._func, Bindable):
            func = self._func.bind(run_hive)
            return self.__class__(func, bound=True)

        else:
            return self
        
    def export(self):
        # TODO: somehow log the redirection path
        func = self._func

        if isinstance(func, Exportable):
            exported = func.export()
            return self.__class__(exported, bound=self._bound)

        else:
            return self
    
    def _hive_connectable_target(self, source):
        # TODO : nicer error message
        assert isinstance(source, Plugin)

    def _hive_connect_target(self, source):
        plugin = source.plugin()
        self._func(plugin)
    

class HiveSocketBee(Socket, ConnectTarget, Exportable):

    def __init__(self, target):
        self._hive_cls = get_building_hive()
        self._target = target

    @manager.getinstance
    def getinstance(self, hiveobject):        
        target = self._target
        if isinstance(target, Bee): 
            target = target.getinstance(hiveobject)

        return HiveSocket(target)

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            exported = target.export()
            return self.__class__(exported)

        else:
            return self


socket = ContextFactory("hive.socket", immediate_cls=HiveSocket, deferred_cls=HiveSocketBee)