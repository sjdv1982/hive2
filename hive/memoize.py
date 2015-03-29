from functools import wraps
from weakref import WeakKeyDictionary


_memoize_results = WeakKeyDictionary()


def method(func):
    """Wrap single-argument function with memoizing decorator

    :param func: callable unbound method
    """
    @wraps(func)
    def wrapper(self):
        try:
            func_results = _memoize_results[func]
        except KeyError:
            func_results = _memoize_results[func] = WeakKeyDictionary()

        try:
            return func_results[self]

        except KeyError:
            result = func_results[self] = func(self)
            return result

    return wrapper