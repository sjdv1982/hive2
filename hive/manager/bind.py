from weakref import WeakKeyDictionary
from .getinstance import partialmethod
import functools

_runhives = WeakKeyDictionary()
_buildclassobjects = WeakKeyDictionary()

def register_runhive(runhive):
  assert runhive not in _runhives, runhive
  _runhives[runhive] = {}

def bind_manager(self, func, runhive):
  assert runhive in _runhives, runhive
  if self not in _runhives[runhive]:
    _runhives[runhive][self] = func(self, runhive)
  return _runhives[runhive][self]
  
def bind(bindfunc):
  func = partialmethod(bind_manager, bindfunc)
  functools.update_wrapper(func, bindfunc)
  return func