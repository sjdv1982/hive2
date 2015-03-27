from .mixins import TriggerTarget, ConnectTarget, TriggerSource, Callable, Bee, Bindable
from .classes import HiveBee
from .context_factory import ContextFactory
from . import manager


class Modifier(TriggerTarget, ConnectTarget, Bindable, Callable):

    def __init__(self, func, bound=False):
        assert callable(func) or isinstance(func, Callable), func
        self._func = func
        self._bound = bound

    def __call__(self):
        self.trigger()

    def trigger(self):
        # TODO: exception handling hooks
        self._func()
        
    @manager.bind
    def bind(self, run_hive):
        if self._bound:
            return self

        func = self._func

        if isinstance(func, Bindable):
            func = func.bind(run_hive)
        
        return self.__class__(func, bound=True)

    def _hive_trigger_target(self):
        return self.trigger
    
    def _hive_connectable_target(self, source):
        # TODO : nicer error message
        assert isinstance(source, TriggerSource)

    def _hive_connect_target(self, source):
        pass


class ModifierBee(TriggerTarget, ConnectTarget, HiveBee):

    def __init__(self, func):
        HiveBee.__init__(self, None, func)

    @manager.getinstance
    def getinstance(self, hive_object):
        func, = self.args
        if isinstance(func, Bee): 
            func = func.getinstance(hive_object)

        return Modifier(func)

    def implements(self, cls):
        if cls is Callable:
            return True

        if HiveBee.implements(self, cls):
            return True

        func, = self.args
        if isinstance(func, Bee):
            return func.implements(cls)

        return False


modifier = ContextFactory("hive.modifier", immediate_cls=Modifier, deferred_cls=ModifierBee)