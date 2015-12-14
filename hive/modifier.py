from .classes import HiveBee
from .manager import ContextFactory, memoize
from .mixins import TriggerTarget, ConnectTarget, TriggerSource, Callable, Bee, Bindable


class Modifier(TriggerTarget, ConnectTarget, Bindable, Callable):
    """Callable Python snippet which is passed the current run hive"""

    def __init__(self, func, run_hive=None):
        assert callable(func) and not isinstance(func, Bee), \
            "Modifier function should be a Python callable, got {}".format(func)
        self._func = func
        self._run_hive = run_hive

    def __call__(self):
        self.trigger()

    def __repr__(self):
        return "<Modifier: {}>".format(self._func)

    def trigger(self):
        # TODO: exception handling hooks
        self._func(self._run_hive)
        
    @memoize
    def bind(self, run_hive):
        if self._run_hive:
            return self

        return self.__class__(self._func, run_hive=run_hive)

    def _hive_trigger_target(self):
        return self.trigger
    
    def _hive_is_connectable_target(self, source):
        if not isinstance(source, TriggerSource):
            raise TypeError("Connect target {} is not a TriggerSource".format(source))

    def _hive_connect_target(self, source):
        pass


class ModifierBee(TriggerTarget, ConnectTarget, Callable, HiveBee):
    """Callable Python snippet which is passed the current run hive"""

    def __init__(self, func):
        super().__init__()

        self._func = func

    def __repr__(self):
        return "<Modifier: {}>".format(self._func)

    @memoize
    def getinstance(self, hive_object):
        func = self._func
        if isinstance(func, Bee): 
            func = func.getinstance(hive_object)

        return Modifier(func)

    def implements(self, cls):
        if Bee.implements(self, cls):
            return True

        func = self._func
        if isinstance(func, Bee):
            return func.implements(cls)

        return False


modifier = ContextFactory("hive.modifier", immediate_mode_cls=Modifier, build_mode_cls=ModifierBee)