from . import manager

_mode = "immediate"
def get_mode():
  return _mode

def set_mode(mode):
  global _mode
  assert mode in ("immediate", "build"), mode
  _mode = mode
    
_building_hive = None
def get_building_hive():
  return _building_hive

def set_building_hive(building_hive):
  global _building_hive  
  assert building_hive is None or issubclass(building_hive, Hive), building_hive
  _building_hive = building_hive


_runhive = None
def get_runhive():
  return _runhive

def set_runhive(runhive):
  global _runhive  
  assert runhive is None or isinstance(runhive, RunHive), runhive
  _runhive = runhive

from .hive import hive, Hive, runhive as RunHive

#i primitives
from .triggerfunc import triggerfunc
from .triggerable import triggerable
#from .modifier import modifier #TODO (akin to triggerable, but receives runhive as self)
from .property import property
#from .buffer import buffer #TODO (akin to property, but is stored on the runhive)
from .ppin import pushin, pullin
from .ppout import pushout, pullout

#connection primitives
from .connect import connect
from .trigger import trigger

#ex primitives
from .entry import entry
from .hook import hook
from .socket import socket
from .plugin import plugin
from .antenna import antenna
from .output import output
#TODO: NO autosocket! instead, add a name argument to sockets and plugins, and an optional "autosocket" argument to HiveObject.__init__
#TODO: supplier, required etc. for sockets/plugins
#TODO: autosocket default policy (for parent and for children) on args object
#  - if there are named sockets, a policy towards the parent MUST be defined
#  - a policy towards the children is optional   