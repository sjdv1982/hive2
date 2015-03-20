from .mixins import Bee, ConnectTarget, TriggerTarget, Exportable
from . import get_mode, get_building_hive

class Entry(Exportable, Bee):
  def __init__(self, target):
    assert isinstance(target, TriggerTarget), target
    self._hivecls = get_building_hive()
    self._target = target
  def export(self):
    #TODO: somehow log the redirection path
    t = self._target
    if isinstance(t, Exportable):
      t = t.export()
    return t  

def entry(target):
  if get_mode() == "immediate":
    raise ValueError("hive.entry cannot be used in immediate mode")
  else:
    return Entry(target)