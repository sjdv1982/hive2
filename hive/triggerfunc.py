from .mixins import TriggerSource, TriggerTarget, ConnectSource, Callable, Bee, Bindable
from .classes import HiveBee, Pusher
from . import get_mode
from . import manager

class TriggerFunc(TriggerSource, ConnectSource, Bindable, Callable):
    def __init__(self, func, bound=False):
        assert callable(func) or func is None or isinstance(func, Callable), func
        self._bound = bound
        self._func = func
        self._trig = Pusher(self)
        self._pretrig = Pusher(self)
        self._namecounter = 0 #TODO
    def __call__(self, *args, **kwargs):
        #TODO: exception handling hooks
        self._pretrig.push()
        if self._func is not None:
            self._func(*args, **kwargs)
        self._trig.push()
    def _hive_trigger_source(self, targetfunc):
        self._namecounter += 1 #TODO
        self._trig.add_target(targetfunc, self._namecounter)
    def _hive_pretrigger_source(self, targetfunc):
        self._namecounter += 1 #TODO
        self._pretrig.add_target(targetfunc, self._namecounter) 
        
    def _hive_connectable_source(self, target):
        assert isinstance(target, TriggerTarget) #TODO : nicer error message
    def _hive_connect_source(self, target):
        targetfunc = target._hive_trigger_target()
        self._trig.add_target(targetfunc)
        
    @manager.bind
    def bind(self, runhive):
        if self._bound: return self
        func = self._func
        if isinstance(func, Bindable):
            func = func.bind(runhive)
        ret = self.__class__(func, bound=True)
        return ret        
    
class TriggerFuncBee(HiveBee, TriggerSource, ConnectSource):
    def __init__(self, func):
        HiveBee.__init__(self, None, func)
    @manager.getinstance
    def getinstance(self, hiveobject):        
        func, = self.args
        if isinstance(func, Bee): 
            func = func.getinstance(hiveobject)            
        ret = TriggerFunc(func)
        return ret
    def implements(self, cls):
        if HiveBee.implements(self, cls):
            return True
        if cls == Callable:
            return True
        func, = self.args
        if isinstance(func, Bee):
            return func.implements(cls)
        return False

def triggerfunc(func=None):
    if get_mode() == "immediate":
        return TriggerFunc(func)
    else:
        return TriggerFuncBee(func)