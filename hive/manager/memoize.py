from weakref import WeakKeyDictionary
from functools import wraps


class Memoizer:

    def __init__(self):
        self._cache = WeakKeyDictionary()

    def __call__(self, func):
        func_instance_cache = self._cache[func] = WeakKeyDictionary()

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


memoize = Memoizer()