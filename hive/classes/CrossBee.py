from ..mixins import Bee, Bindable

class CrossBee(Bee):
  def __init__(self, bee, ownhiveobject):
    self._bee = bee
    self._ownhiveobject = ownhiveobject
  def getinstance(self, hiveobject): 
    rhive = self._ownhiveobject.getinstance(hiveobject)    
    ret = self._bee.getinstance(rhive._hive_object)
    if isinstance(ret, Bindable):
      ret = ret.bind(rhive)
    return ret
  def implements(self, cls):
    return self._bee.implements(cls)
  def __getattr__(self, attr):
    if attr.startswith("_"):
      return object.__getattribute__(self, attr)
    return getattr(self._bee, attr)