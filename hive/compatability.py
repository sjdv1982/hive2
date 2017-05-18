from inspect import isfunction


try:
    advance_iterator = next

except NameError:
    def advance_iterator(it):
        return it.next()


next = advance_iterator


def is_method(func):
    """Test if value is a callable method.

    Python 3 disposes of this notion, so we only need check if it is callable.
    """
    if hasattr(func, "im_class"):
        return True

    return isfunction(func)


def validate_signature(obj, *args, **kwargs):
    """Check call signature is satisfied by provided args"""
    try:
        from inspect import signature

    except ImportError:
        from inspect import isclass, ismethod, getcallargs

        if isclass(obj):
            pass

        obj = obj.__init__

        if ismethod(obj):
            if obj.im_self is not None:
                pass

            else:
                args = (None,) + args

        try:
            getcallargs(obj, *args, **kwargs)

        except Exception as err:
            raise TypeError(err)

    else:
        sig = signature(obj)
        sig.bind(*args, **kwargs)


try:
    from functools import lru_cache as cache

except ImportError:
    from .manager import memoize as _memoize
    def cache(maxsize=None):
        return _memoize