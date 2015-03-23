from weakref import WeakKeyDictionary
from .getinstance import partialmethod
import functools


_run_hives = WeakKeyDictionary()
_buildclassobjects = WeakKeyDictionary()


def register_run_hive(run_hive):
    assert run_hive not in _run_hives, run_hive
    _run_hives[run_hive] = {}


def bind_manager(self, func, run_hive):
    assert run_hive in _run_hives, run_hive
    if self not in _run_hives[run_hive]:
        _run_hives[run_hive][self] = func(self, run_hive)
    return _run_hives[run_hive][self]


def bind(bindfunc):
    func = partialmethod(bind_manager, bindfunc)
    functools.update_wrapper(func, bindfunc)
    return func