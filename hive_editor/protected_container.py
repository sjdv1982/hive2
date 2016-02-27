from contextlib import contextmanager
from weakref import WeakKeyDictionary


class ProtectedContainer(object):

    def __init__(self):
        self._is_guarded = True

    @property
    def is_guarded(self):
        return self._is_guarded

    @contextmanager
    def make_writable(self):
        self._is_guarded = False
        yield
        self._is_guarded = True


class RestrictedAttribute(object):

    def __init__(self):
        self._data = WeakKeyDictionary()

    def __get__(self, instance, cls=None):
        return self._data[instance]

    def __set__(self, instance, value):
        if instance.is_guarded:
            raise AttributeError("Instance not writable")

        self._data[instance] = value


class RestrictedProperty(object):

    def __init__(self, fget, fset=None, fget_free=None):
        self._fget = fget
        self._fset = fset
        self._fget_free = fget_free

    def setter(self, fset):
        return RestrictedProperty(self._fget, fset, self._fget_free)

    def guarded_getter(self, fget):
        return RestrictedProperty(self._fget, self._fset, fget)

    def __get__(self, instance, cls=None):
        if instance is not None:
            if instance.is_guarded:
                return self._fget.__get__(instance)()

            return self._fget_free.__get__(instance)()

        return self

    def __set__(self, instance, value):
        if instance.is_guarded:
            raise AttributeError("Instance not writable")

        self._fset.__get__(instance)(value)