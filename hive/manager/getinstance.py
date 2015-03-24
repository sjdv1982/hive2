from weakref import WeakKeyDictionary
import functools
from functools import partial


_hive_objects = WeakKeyDictionary()


class PartialMethod(partial):
    """Partial function for instance methods

    snippet retrieved from https://gist.github.com/carymrobbins/8940382
    """

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return partial(self.func, instance, *(self.args or ()), **(self.keywords or {}))


def register_hive_object(hive_object):
    """Register hive object for later getinstance cache

    :param hive_object: HiveObject instance
    """
    if hive_object not in _hive_objects:
        _hive_objects[hive_object] = {}


def getinstance_manager(self, func, hive_object):
    """Memoizing instance manager.

    :param self: bee instance
    :param func: getinstance function
    :param hive_object: hive object to which this instance belongs.

    Returns cached instance for hive object, calling bound function if it does not exist
    """
    assert hive_object in _hive_objects, hive_object
    if self not in _hive_objects[hive_object]:
        _hive_objects[hive_object][self] = func(self, hive_object)

    return _hive_objects[hive_object][self]


def getinstance(getinstance_func):
    """Memoizing decorator to cache successive getinstance calls

    :param getinstance_func: getinstance function (called once)
    """
    func = PartialMethod(getinstance_manager, getinstance_func)
    functools.update_wrapper(func, getinstance_func)
    return func