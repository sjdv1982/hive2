from weakref import WeakKeyDictionary
from functools import wraps


_memoize_cache = WeakKeyDictionary()


def memoize(func):
    """Memoizing decorator

    Cache function call results for similar arguments
    """
    func_instance_cache = _memoize_cache[func] = WeakKeyDictionary()

    @wraps(func)
    def wrapper(self, *args):
        try:
            results_cache = func_instance_cache[self]

        except KeyError:
            results_cache = func_instance_cache[self] = {}

        try:
            return results_cache[args]

        except KeyError:
            result = results_cache[args] = func(self, *args)
            return result

    return wrapper