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
            return _memoize_results[func]

        except KeyError:
            _memoize_results[func] = func(self)
            return _memoize_results[func]

    return wrapper