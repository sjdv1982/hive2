from .mixins import TriggerSource, TriggerTarget, ConnectSource, Callable, Bee, Bindable
from .classes import HiveBee, Pusher
from .manager import ContextFactory, memoize


class TriggerFunc(TriggerSource, ConnectSource, Bindable, Callable):
    """Callable interface to HIVE (pre)trigger"""

    def __init__(self, func=None, bound=None):
        assert callable(func) or func is None or isinstance(func, Callable), func
        self._bound = bound
        self._func = func
        self._trigger = Pusher(self)
        self._pretrigger = Pusher(self)
        # TODO
        self._name_counter = 0

    def __call__(self, *args, **kwargs):
        # TODO: exception handling hooks
        self._pretrigger.push()
        if self._func is not None:
            self._func(*args, **kwargs)

        self._trigger.push()

    def _hive_trigger_source(self, target_func):
        self._name_counter += 1
        self._trigger.add_target(target_func, self._name_counter)

    def _hive_pretrigger_source(self, target_func):
        self._name_counter += 1
        self._pretrigger.add_target(target_func, self._name_counter)
        
    def _hive_is_connectable_source(self, target):
        # TODO : nicer error message
        assert isinstance(target, TriggerTarget)

    def _hive_connect_source(self, target):
        target_func = target._hive_trigger_target()
        self._trigger.add_target(target_func)
        
    @memoize
    def bind(self, run_hive):
        if self._bound:
            return self

        func = self._func
        if isinstance(func, Bindable):
            func = func.bind(run_hive)

        return self.__class__(func, bound=run_hive)


class TriggerFuncBee(HiveBee, TriggerSource, ConnectSource):

    def __init__(self, func=None):
        HiveBee.__init__(self, None, func)

    @memoize
    def getinstance(self, hive_object):
        func, = self.args
        if isinstance(func, Bee): 
            func = func.getinstance(hive_object)

        return TriggerFunc(func)

    def implements(self, cls):
        if HiveBee.implements(self, cls):
            return True

        if cls is Callable:
            return True

        func, = self.args
        if isinstance(func, Bee):
            return func.implements(cls)

        return False


triggerfunc = ContextFactory("hive.triggerfunc", immediate_cls=TriggerFunc, deferred_cls=TriggerFuncBee)