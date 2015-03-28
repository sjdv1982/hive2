from ..mixins import Exportable


class HiveExportables(object):

    def __init__(self, hive_cls):
        assert hive_cls is not None
        self._hive_cls = hive_cls
        self._bee_names = set()

    def __setattr__(self, name, value):
        if name == "parent":
            raise AttributeError("HiveExportables (ex) special attribute 'parent' cannot be assigned to"
                                 % value.__class__)

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        if value is None:
            if hasattr(self, name):
                self.__delattr__(name)

            return

        if not isinstance(value, Exportable):
            raise TypeError("HiveExportables (ex) attribute must be an Exportable, not '%s'" % value.__class__)

        if value._hive_cls is None:
            raise AttributeError("HiveExportables (ex) attribute '%s' must contain a Bee built by '%s' (or one of its b"
                                 "ase classes), but the Bee was not built by any hive" % (name, self._hive_cls.__name__))

        if not issubclass(value._hive_cls, self._hive_cls):
            raise AttributeError("HiveExportables (ex) attribute '%s' must contain a Bee built by '%s' (or one of its"
                                 " base classes), not '%s'" % (name, self._hive_cls.__name__, value._hive_cls.__name__))

        self._bee_names.add(name)
        object.__setattr__(self, name, value)

    def __delattr__(self, attr):
        if attr not in self._bee_names:
            raise AttributeError

        self._bee_names.remove(attr)
        object.__delattr__(self, attr)

    def __dir__(self):
        return list(self._bee_names)