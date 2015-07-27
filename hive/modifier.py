from .mixins import TriggerTarget, ConnectTarget, TriggerSource, Callable, Bee, Bindable
from .classes import HiveBee
from .manager import ContextFactory, memoize


class Modifier(TriggerTarget, ConnectTarget, Bindable, Callable):

    def __init__(self, func, bound=None):
        assert callable(func) and not isinstance(func, Bee), \
            "Modifier function should be a Python callable, got {}".format(func)
        self._func = func
        self._bound = bound

    def __call__(self):
        self.trigger()

    def __repr__(self):
        return "<Modifier: {}>".format(self._func)

    def trigger(self):
        # TODO: exception handling hooks
        self._func(self._bound)
        
    @memoize
    def bind(self, run_hive):
        if self._bound:
            return self

        return self.__class__(self._func, bound=run_hive)

    def _hive_trigger_target(self):
        return self.trigger
    
    def _hive_is_connectable_target(self, source):
        # TODO : nicer error message
        assert isinstance(source, TriggerSource)

    def _hive_connect_target(self, source):
        pass


class ModifierBee(TriggerTarget, ConnectTarget, HiveBee):

    def __init__(self, func):
        HiveBee.__init__(self, None, func)

    def __repr__(self):
        return "<Modifier: {}>".format(self.args[0])

    @memoize
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


modifier = ContextFactory("hive.modifier", immediate_mode_cls=Modifier, build_mode_cls=ModifierBee)