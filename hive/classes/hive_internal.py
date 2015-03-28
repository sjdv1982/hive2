from ..mixins import Bee, Exportable


class HiveInternals(object):

    def __init__(self, hive_cls):
        assert hive_cls is not None
        self._hive_cls = hive_cls
        self._bee_names = set()

    def __setattr__(self, name, value):
        if name == "parent":
            raise AttributeError("HiveInternals (i) special attribute 'parent' cannot be assigned to" % value.__class__)

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        # Mechanism for deletion of attributes
        if value is None:
            if hasattr(self, name):
                self.__delattr__(name)

            return

        if not isinstance(value, Bee):
            raise TypeError("HiveInternals (i) attribute '%s' must be a Bee, not '%s'" % (name,    value.__class__))

        if isinstance(value, Exportable) and value.export_only:
            raise TypeError("HiveInternals (i) attribute '%s' must not be Exportable; Exportables must be added to ex"
                            % name)

        if value._hive_cls is None:
            raise AttributeError("HiveInternals (i) attribute '%s' must contain a Bee built by '%s' (or one of its base"
                                 " classes), but the Bee was not built by any hive" % (name, self._hive_cls.__name__))

        if not issubclass(value._hive_cls, self._hive_cls):
            raise AttributeError("HiveInternals (i) attribute '%s' must contain a Bee built by '%s' (or one of its base"
                                 " classes), not '%s'" % (name, self._hive_cls.__name__, value._hive_cls.__name__))

        self._bee_names.add(name)
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name not in self._bee_names:
            raise AttributeError

        self._bee_names.remove(name)
        object.__delattr__(self, name)

    def __dir__(self):
        return list(self._bee_names)
