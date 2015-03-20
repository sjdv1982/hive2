from .mixins import TriggerSource, TriggerTarget, Bee, Bindable
from .classes import HiveBee
from . import get_mode
from . import manager
from .hive import HiveObject

def build_trigger(source, target, pre):
  #TODO: register connection, or insert a listener function in between  
  targetfunc = target._hive_trigger_target()
  if pre:
    source._hive_pretrigger_source(targetfunc)
  else:
    source._hive_trigger_source(targetfunc)
  
class Trigger(Bindable):
  def __init__(self, source, target, pretrigger):
    self.source = source
    self.target = target
    self.pretrigger = pretrigger
  @manager.bind
  def bind(self, runhive):
    source = self.source
    if isinstance(source, Bindable):
      source = source.bind(runhive)
    target = self.target
    if isinstance(target, Bindable):
      target = target.bind(runhive)
    return build_trigger(source, target, self.pretrigger)  
  
class TriggerBee(HiveBee):  
  def __init__(self, source, target, pretrigger):
    HiveBee.__init__(self, None, source, target, pretrigger)
  @manager.getinstance
  def getinstance(self, hiveobject):
    source, target, pretrigger = self.args
    if isinstance(source, HiveObject):
      source = source.get_trigger_source()
    if isinstance(source, Bee):
      source = source.getinstance(hiveobject)
    if isinstance(target, HiveObject):
      target = target.get_trigger_target()      
    if isinstance(target, Bee):  
      target = target.getinstance(hiveobject)                          
    if get_mode() == "immediate":      
      return build_trigger(source, target, pretrigger)
    else:
      return Trigger(source, target, pretrigger)
        
def _trigger(source, target,pretrigger):  
  if isinstance(source, Bee):
    assert source.implements(TriggerSource), source
    assert target.implements(TriggerTarget), target
  else:
    assert isinstance(source, TriggerSource), source
    assert isinstance(target, TriggerTarget), target  
  if get_mode() == "immediate":
    build_trigger(source, target,pretrigger)
  else:
    triggerbee = TriggerBee(source, target, pretrigger)    
    manager.register_bee(triggerbee)
    return triggerbee
    
def trigger(source, target,pre=False):
  return _trigger(source,target,pre)
