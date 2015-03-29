from .mixins import Plugin, Socket, ConnectSource, Exportable, Callable, Bee, Bindable
from .context_factory import ContextFactory
from . import manager
from . import get_building_hive


class HivePlugin(Plugin, ConnectSource, Bindable, Exportable):

    def __init__(self, func, name = None, data_type = (), bound = False, exported = False):
        assert callable(func) or isinstance(func, Callable), func
        self._exported = False
        self._func = func
        self._bound = bound
        self.name = name
        self.data_type = data_type        

    def plugin(self):
        return self._func
        
    def _hive_connectable_source(self, target):
        assert isinstance(target, Socket), target # TODO : nicer error message

    def _hive_connect_source(self, target):
        pass
        
    def export(self):
        if self._exported:
            return self
        
        # TODO: somehow log the redirection path
        func = self._func

        if isinstance(func, Exportable):
            exported = func.export()
            return self.__class__(exported, self.name, self.data_type, bound=self._bound, exported=True)

        else:
            return self
        
    @manager.bind
    def bind(self, run_hive):
        if self._bound: 
            return self

        if isinstance(self._func, Bindable):
            func = self._func.bind(run_hive)
            return self.__class__(func, self.name, self.data_type, bound=True)

        else:
            return self


class HivePluginBee(Plugin, ConnectSource, Exportable):

    def __init__(self, target, name=None, data_type=(), exported=False):
        self._hive_cls = get_building_hive()
        self._target = target
        self._exported = exported
        self.name = name
        self.data_type = data_type

    @manager.getinstance
    def getinstance(self, hive_object):
        target = self._target

        if isinstance(target, Bee):
            target = target.getinstance(hive_object)

        return HivePlugin(target, self.name, self.data_type)

    def export(self):
        if self._exported:
            return self
          
        # TODO: somehow log the redirection path
        target = self._target

        if isinstance(target, Exportable):
            exported = target.export()
            return self.__class__(exported, self.name, self.data_type, exported=True)

        else:
            return self


plugin = ContextFactory("hive.plugin", immediate_cls=HivePlugin, deferred_cls=HivePluginBee)