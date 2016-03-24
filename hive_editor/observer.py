from traceback import print_exc
from weakref import WeakKeyDictionary


class ObservableInstance:
    """Implements the Observer pattern to notify arbitrary listeners of events"""

    def __init__(self):
        self._observers = []

    def clear(self):
        """Unsubscribe all observers"""
        self._observers.clear()

    def subscribe(self, observer):
        """Add an observer to the observer list"""
        self._observers.append(observer)

    def unsubscribe(self, observer):
        """Remove an observer from the observer list"""
        self._observers.remove(observer)

    def __call__(self, *args, **kwargs):
        """Call all observers with provided arguments"""
        for observer in self._observers:
            try:
                observer(*args, **kwargs)

            except Exception as err:
                print_exc()


class Observable:
    """Descriptor object to instantiate ObservableInstance for class instances"""

    def __init__(self):
        self._instances = WeakKeyDictionary()

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        try:
            return self._instances[instance]

        except KeyError:
            observable = self._instances[instance] = ObservableInstance()
            return observable

    def __set__(self, instance, value):
        raise AttributeError("Observable cannot be set")
