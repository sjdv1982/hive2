from .mixins import TriggerSource, TriggerTarget, ConnectSource, Callable, Bee, Bindable
from .classes import HiveBee, Pusher
from .context_factory import ContextFactory
from . import manager


class TriggerFunc(TriggerSource, ConnectSource, Bindable, Callable):

    def __init__(self, func=None, bound=False):
        assert callable(func) or func is None or isinstance(func, Callable), func
        self._bound = bound
        self._func = func
        self._trigger = Pusher(self)
        self._pre_trigger = Pusher(self)
        # TODO
        self._name_counter = 0

    def __call__(self, *args, **kwargs):
        # TODO: exception handling hooks
        self._pre_trigger.push()
        if self._func is not None:
            self._func(*args, **kwargs)

        self._trigger.push()

    def _hive_trigger_source(self, targetfunc):
        self._name_counter += 1
        self._trigger.add_target(targetfunc, self._name_counter)

    def _hive_pretrigger_source(self, targetfunc):
        self._name_counter += 1
        self._pre_trigger.add_target(targetfunc, self._name_counter)
        
    def _hive_connectable_source(self, target):
        # TODO : nicer error message
        assert isinstance(target, TriggerTarget)

    def _hive_connect_source(self, target):
        target_func = target._hive_trigger_target()
        self._trigger.add_target(target_func)
        
    @manager.bind
    def bind(self, run_hive):
        if self._bound:
            return self

        func = self._func
        if isinstance(func, Bindable):
            func = func.bind(run_hive)

        return self.__class__(func, bound=True)


class TriggerFuncBee(HiveBee, TriggerSource, ConnectSource):

    def __init__(self, func=None):
        HiveBee.__init__(self, None, func)

    @manager.getinstance
    def getinstance(self, hive_object):
        func, = self.args
        if isinstance(func, Bee): 
            func = func.getinstance(hive_object)

        return TriggerFunc(func)

    def implements(self, cls):
        if HiveBee.implements(self, cls):
            return True

        if cls == Callable:
            return True

        func, = self.args
        if isinstance(func, Bee):
            return func.implements(cls)

        return False


triggerfunc = ContextFactory("hive.triggerfunc", immediate_cls=TriggerFunc, deferred_cls=TriggerFuncBee)