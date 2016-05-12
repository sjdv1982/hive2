from contextlib import contextmanager
from weakref import WeakKeyDictionary


class ProtectedContainer(object):
    """Base class for implementing guarded attributes"""

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
    """Readable instance attribute that can be written to within the ProtectedContainer.make_writable() context"""

    def __init__(self):
        self._data = WeakKeyDictionary()

    def __get__(self, instance, cls=None):
        return self._data[instance]

    def __set__(self, instance, value):
        if instance.is_guarded:
            raise AttributeError("Instance not writable")

        self._data[instance] = value


class RestrictedProperty(object):
    """Property descriptor which is writable within the ProtectedContainer.make_writable() context, and calls one of
    two getter methods when read, depending upon the instance.is_guarded state
    """

    def __init__(self, fget, fset=None, fget_unrestricted=None):
        self._fget = fget
        self._fset = fset
        self._fget_restricted = fget_unrestricted

    def setter(self, fset):
        return RestrictedProperty(self._fget, fset, self._fget_restricted)

    def restricted_getter(self, fget):
        return RestrictedProperty(self._fget, self._fset, fget)

    def __get__(self, instance, cls=None):
        if instance is not None:
            if instance.is_guarded:
                return self._fget.__get__(instance)()

            return self._fget_restricted.__get__(instance)()

        return self

    def __set__(self, instance, value):
        if instance.is_guarded:
            raise AttributeError("Instance not writable")

        self._fset.__get__(instance)(value)