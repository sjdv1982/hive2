from .mixins import TriggerTarget, ConnectTarget, TriggerSource, Callable, Bee, Bindable
from .classes import HiveBee
from . import get_mode, manager

class Triggerable(TriggerTarget, ConnectTarget, Bindable, Callable):
  def __init__(self, func, bound=False):
    assert callable(func) or isinstance(func, Callable), func
    self._func = func
    self._bound = bound
  def trigger(self):
    #TODO: exception handling hooks
    self._func()
  def __call__(self):
    self.trigger()
    
  @manager.bind
  def bind(self, runhive):
    if self._bound: return self
    func = self._func
    if isinstance(func, Bindable):
      func = func.bind(runhive)
    ret = self.__class__(func, bound=True)
    return ret
  def _hive_trigger_target(self):
    return self.trigger
  
  def _hive_connectable_target(self, source):
    assert isinstance(source, TriggerSource) #TODO : nicer error message
  def _hive_connect_target(self, source):
    pass
  
class TriggerableBee(TriggerTarget, ConnectTarget, HiveBee):
  def __init__(self, func):
    HiveBee.__init__(self, None, func)
  @manager.getinstance
  def getinstance(self, hiveobject):        
    func, = self.args
    if isinstance(func, Bee): 
      func = func.getinstance(hiveobject)      
    ret = Triggerable(func)
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

def triggerable(func):
  if get_mode() == "immediate":
    return Triggerable(func)
  else:
    return TriggerableBee(func)