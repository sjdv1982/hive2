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


