from weakref import WeakKeyDictionary
import functools
from functools import partial

###
#snippet retrieved from https://gist.github.com/carymrobbins/8940382
class partialmethod(partial):
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return partial(self.func, instance,
                       *(self.args or ()), **(self.keywords or {}))
###

_hiveobjects = WeakKeyDictionary()

def register_hiveobject(hiveobject):
  if hiveobject not in _hiveobjects:
    _hiveobjects[hiveobject] = {}

def getinstance_manager(self, func, hiveobject):
  assert hiveobject in _hiveobjects, hiveobject
  if self not in _hiveobjects[hiveobject]:
    _hiveobjects[hiveobject][self] = func(self, hiveobject)
  return _hiveobjects[hiveobject][self]
  
def getinstance(getinstancefunc):
  func = partialmethod(getinstance_manager, getinstancefunc)
  functools.update_wrapper(func, getinstancefunc)
  return func