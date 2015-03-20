from .mixins import Plugin, Socket, ConnectSource, Exportable, Callable, Bee, Bindable
from .classes import HiveBee
from . import get_mode
from . import manager
from . import get_building_hive

class HivePlugin(Plugin, ConnectSource, Bindable, Exportable):
  def __init__(self, func,bound=False):
    assert callable(func) or isinstance(func, Callable), func
    self._func = func
    self._bound = bound
  def plugin(self):
    return self._func
    
  def _hive_connectable_source(self, target):
    assert isinstance(target, Socket), target #TODO : nicer error message
  def _hive_connect_source(self, target):
    pass
    
  def export(self):
    #TODO: somehow log the redirection path
    t = self._func
    if isinstance(t, Exportable):
      e = t.export()
      return self.__class__(e, bound=self._bound)
    else:
      return self
    
  @manager.bind
  def bind(self, runhive):
    if self._bound: 
      return self    
    if isinstance(self._func, Bindable):
      func = self._func.bind(runhive)
      return self.__class__(func, bound=True)
    else:
      return self

class HivePluginBee(Plugin, ConnectSource, Exportable):
  def __init__(self, target):
    self._hivecls = get_building_hive()
    self._target = target
  @manager.getinstance
  def getinstance(self, hiveobject):    
    target = self._target
    if isinstance(target, Bee): 
      target = target.getinstance(hiveobject)      
    ret = HivePlugin(target)
    return ret
  def export(self):
    #TODO: somehow log the redirection path
    target = self._target
    if isinstance(target, Exportable):
      e = target.export()
      return self.__class__(e)
    else:
      return self
    
def plugin(func):
  if get_mode() == "immediate":
    return HivePlugin(func)
  else:
    return HivePluginBee(func)