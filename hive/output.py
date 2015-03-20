"""
from .mixins import Antenna, Output, Stateful, Bee, Bindable, Exportable
from .mixins import ConnectSource, ConnectTarget, TriggerSource, TriggerTarget, Socket, Plugin
from .classes import HiveBee, Pusher
from . import get_mode
from . import manager
from .antenna import compare_types

class OutputBase(Output, ConnectSource, TriggerSource, Bindable):
  def __init__(self, target, datatype, bound=False, runhive=None):
    assert isinstance(target, Stateful) or target.implements(Callable), target
    self._stateful = isinstance(target, Stateful)
    self.target = target
    self.datatype = datatype
    self._bound = bound
    self._runhive = runhive
    self._trig = Pusher(self)
    self._pretrig = Pusher(self)        
        
  @manager.bind
  def bind(self, runhive):
    self._runhive = runhive
    if self._bound: return self
    target = self.target
    if isinstance(target, Bindable):
      target = target.bind(runhive)
    ret = self.__class__(target, self.datatype, bound=True, runhive=runhive)
    return ret    

  def _hive_trigger_source(self, targetfunc):
    self._trig.add_target(targetfunc)
  def _hive_pretrigger_source(self, targetfunc):
    self._pretrig.add_target(targetfunc)

class PullOutput(OutputBase):
  mode = "pull"
  def pull(self):
    #TODO: exception handling hooks
    self._pretrig.push()
    if self._stateful:
      value = self.target._hive_stateful_getter(self._runhive)
    else:
      value = self.target()
    self._trig.push()
    return value
  def _hive_connectable_source(self, target):
    assert isinstance(target, Antenna) #TODO : nicer error message
    assert target.mode == "pull" #TODO : nicer error message
    compare_types(self, target)
  def _hive_connect_source(self, target):
    pass    
  
class PushOutput(OutputBase, Socket, ConnectTarget, TriggerTarget):
  mode = "push"
  def __init__(self, target, datatype, bound=False, runhive=None):
    OutputBase.__init__(self, target, datatype, bound, runhive)
    self._targets = []
  def push(self):
    #TODO: exception handling hooks
    self._pretrig.push()
    if self._stateful:
      value = self.target._hive_stateful_getter(self._runhive)    
    else:
      value = self.target()
    for target in self._targets:
      target(value)
    self._trig.push()
  def socket(self):
    return self.push
  
  def _hive_connectable_source(self, target):
    assert isinstance(target, Antenna), target #TODO : nicer error message
    assert source.mode == "push" #TODO : nicer error message  
    compare_types(target, self)
  def _hive_connect_source(self, target):
    self._targets.append(target.push)
      
  def _hive_connectable_target(self, source):
    assert isinstance(source, Plugin), source #TODO : nicer error message      
  def _hive_connect_target(self, source):
    self._targets.append(source.plugin)
      
  def _hive_trigger_target(self):
    return self.push
  

class OutputBee(HiveBee, Output, ConnectSource, TriggerSource, Exportable):
  def __init__(self, mode, target, *datatype):
    assert mode in ("push", "pull")
    self.mode = mode
    self.datatype = datatype #TODO: retrieve datatype info from target and check that it matches (TODO add it to h.property and h.buffer)
    assert isinstance(target, Stateful) or isinstance(target,Output) or target.implements(Callable) #TODO: nice error message
    HiveBee.__init__(self, None, target)
  @manager.getinstance
  def getinstance(self, hiveobject):    
    target, = self.args
    if isinstance(target, Bee): 
      target = target.getinstance(hiveobject)      
    if self.mode == "push":  
      ret = PushOutput(target, self.datatype)  
    else:
      ret = PullOutput(target, self.datatype)  
    return ret
  def export(self):
    target, = self.args
    if isinstance(target, Stateful):
      return self
    elif isinstance(target, Exportable):
      return target.export()
    else:
      return target
  def implements(self, cls):
    if HiveBee.implements(self, cls):
      return True
    if cls == TriggerTarget and self.mode == "push":
      return True
    return False
    
def output(mode, target, *datatype):
  assert mode in ("push", "pull"), mode #TODO: nicer error message
  assert isinstance(target, Bee), target #TODO: nicer error message  
  if get_mode() == "immediate":
    if isinstance(target, Exportable):
      target = target.export()    
    assert isinstance(target, Stateful) or target.implements(Callable) #TODO: nicer error message
    if mode == "push":
      return PushOutput(target, *datatype)    
    else:
      return PullOutput(target, *datatype)    
  else:
    return OutputBee(mode, target, *datatype)
"""
from .mixins import Bee, Output, Exportable
from . import get_mode, get_building_hive

class HiveOutput(Output, Exportable):
  def __init__(self, target):
    assert isinstance(target, Output), target
    self._hivecls = get_building_hive()
    self._target = target
  def export(self):
    #TODO: somehow log the redirection path
    t = self._target
    if isinstance(t, Exportable):
      t = t.export()
    return t  

def output(target):
  if get_mode() == "immediate":
    raise ValueError("hive.output cannot be used in immediate mode")
  else:
    return HiveOutput(target)