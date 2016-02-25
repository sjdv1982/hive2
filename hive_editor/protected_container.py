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


class RestrictedProperty(object):

    def __init__(self):
        self._data = WeakKeyDictionary()

    def __get__(self, instance, cls=None):
        return self._data[instance]

    def __set__(self, instance, value):
        if instance.is_guarded:
            raise AttributeError("Instance not writable")

        self._data[instance] = value
