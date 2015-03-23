from weakref import WeakKeyDictionary
import functools
from functools import partial

###
#snippet retrieved from https://gist.github.com/carymrobbins/8940382
class partial_method(partial):

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return partial(self.func, instance, *(self.args or ()), **(self.keywords or {}))
###

_hive_objects = WeakKeyDictionary()


def register_hive_object(hive_object):
    if hive_object not in _hive_objects:
        _hive_objects[hive_object] = {}


def getinstance_manager(self, func, hive_object):
    assert hive_object in _hive_objects, hive_object
    if self not in _hive_objects[hive_object]:
        _hive_objects[hive_object][self] = func(self, hive_object)

    return _hive_objects[hive_object][self]


def getinstance(getinstance_func):
    func = partial_method(getinstance_manager, getinstance_func)
    functools.update_wrapper(func, getinstance_func)
    return func