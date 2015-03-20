from .mixins import ConnectTarget, Plugin, Socket, Callable, Exportable, Bee, Bindable
from .classes import HiveBee
from . import get_mode, manager
from . import get_building_hive

class HiveSocket(Socket, ConnectTarget, Bindable, Exportable):
  def __init__(self, func, bound=False):
    assert callable(func) or isinstance(func, Callable), func
    self._func = func
    self._bound = bound
  @manager.bind
  def bind(self, runhive):
    if self._bound: 
      return self
    if isinstance(self._func, Bindable):
      func = self._func.bind(runhive)
      return self.__class__(func, bound=True)
    else:
      return self
    
  def export(self):
    #TODO: somehow log the redirection path
    t = self._func
    if isinstance(t, Exportable):
      e = t.export()      
      return self.__class__(e, bound=self._bound)
    else:
      return self
  
  def _hive_connectable_target(self, source):
    assert isinstance(source, Plugin) #TODO : nicer error message
  def _hive_connect_target(self, source):
    plugin = source.plugin()
    self._func(plugin)
  

class HiveSocketBee(Socket, ConnectTarget, Exportable):
  def __init__(self, target):
    self._hivecls = get_building_hive()
    self._target = target
  @manager.getinstance
  def getinstance(self, hiveobject):    
    target = self._target
    if isinstance(target, Bee): 
      target = target.getinstance(hiveobject)      
    ret = HiveSocket(target)
    return ret
  def export(self):
    #TODO: somehow log the redirection path
    target = self._target
    if isinstance(target, Exportable):
      e = target.export()
      return self.__class__(e)
    else:
      return self

def socket(func):
  if get_mode() == "immediate":
    return HiveSocket(func)
  else:
    return HiveSocketBee(func)