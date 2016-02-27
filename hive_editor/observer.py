from traceback import print_exc
from weakref import WeakKeyDictionary


class ObservableInstance:

    def __init__(self):
        self._observers = []

    def clear(self):
        self._observers.clear()

    def unsubscribe(self, observer):
        self._observers.remove(observer)

    def subscribe(self, observer):
        self._observers.append(observer)

    def __call__(self, *args, **kwargs):
        for observer in self._observers:
            try:
                observer(*args, **kwargs)

            except Exception as err:
                print_exc()


class Observable:

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