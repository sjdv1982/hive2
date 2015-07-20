from .mixins import TriggerTarget, ConnectTarget, TriggerSource, Callable, Bee, Bindable
from .classes import HiveBee
from .manager import ContextFactory, memoize


class Triggerable(TriggerTarget, ConnectTarget, Bindable, Callable):

    def __init__(self, func, bound=None):
        assert callable(func) or isinstance(func, Callable), func
        self._func = func
        self._bound = bound

    def __call__(self):
        self.trigger()

    def trigger(self):
        # TODO: exception handling hooks
        self._func()
        
    @memoize
    def bind(self, run_hive):
        if self._bound:
            return self

        func = self._func

        if isinstance(func, Bindable):
            func = func.bind(run_hive)

        return self.__class__(func, bound=run_hive)

    def _hive_trigger_target(self):
        return self.trigger
    
    def _hive_is_connectable_target(self, source):
        # TODO : nicer error message
        assert isinstance(source, TriggerSource)

    def _hive_connect_target(self, source):
        pass


class TriggerableBee(TriggerTarget, ConnectTarget, HiveBee):

    def __init__(self, func):
        HiveBee.__init__(self, None, func)

    @memoize
    def getinstance(self, hive_object):
        func, = self.args
        if isinstance(func, Bee): 
            func = func.getinstance(hive_object)

        return Triggerable(func)

    def implements(self, cls):
        if cls is Callable:
            return True

        if HiveBee.implements(self, cls):
            return True

        func, = self.args
        if isinstance(func, Bee):
            return func.implements(cls)

        return False


triggerable = ContextFactory("hive.triggerable", immediate_cls=Triggerable, deferred_cls=TriggerableBee)