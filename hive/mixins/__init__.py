class Bee(object):
  _hive_cls = None
  def implements(self, cls):
    return isinstance(self, cls)
  def getinstance(self, hiveobject):
    return self

class Connectable(object):
  #Connectables don't need to be Bees!
  pass

class Bindable(object):
  #Connectables don't need to be Bees!
  pass

class Callable(Bee):
  pass

class Exportable(Bee):
  def export(self):
    raise NotImplementedError

class Plugin(Bee):
  pass

class Socket(Bee):
  pass

class Antenna(Bee):
  mode = None #must be push or pull
  def push(self): #only needs to be defined if mode is "push"
    raise NotImplementedError 

class Output(Bee):
  mode = None #must be push or pull
  def pull(self): #only needs to be defined if mode is "pull"
    raise NotImplementedError 

from .Stateful import Stateful
from .ConnectSource import ConnectSourceBase, ConnectSource, ConnectSourceDerived
from .ConnectTarget import ConnectTargetBase, ConnectTarget, ConnectTargetDerived
from .TriggerSource import TriggerSource
from .TriggerTarget import TriggerTarget
