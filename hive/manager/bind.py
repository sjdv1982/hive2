from weakref import WeakKeyDictionary
from .getinstance import PartialMethod
import functools


_run_hives = WeakKeyDictionary()
_build_class_objects = WeakKeyDictionary()


def register_run_hive(run_hive):
    assert run_hive not in _run_hives, run_hive
    _run_hives[run_hive] = {}


def bind_manager(self, func, run_hive):
    assert run_hive in _run_hives, run_hive
    if self not in _run_hives[run_hive]:
        _run_hives[run_hive][self] = func(self, run_hive)

    return _run_hives[run_hive][self]


def bind(bind_func):
    func = PartialMethod(bind_manager, bind_func)
    functools.update_wrapper(func, bind_func)
    return func