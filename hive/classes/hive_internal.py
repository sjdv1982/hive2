from ..mixins import Bee, Exportable
from . import SPECIAL_NAMES


class HiveInternals(object):

    def __init__(self, hive_object_cls):
        assert hive_object_cls is not None
        self._hive_object_cls = hive_object_cls
        self._bee_names = set()

    def __setattr__(self, name, value):
        if name in SPECIAL_NAMES:
            raise AttributeError("HiveInternals (i) special attribute '%s' cannot be assigned to" % name)

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

        if value._hive_object_cls is None:
            raise AttributeError("HiveInternals (ex) attribute '%s' must contain a Bee built by '%s' (or one of its b"
                                 "ase classes), but the Bee was not built by any hive" % (name, self._hive_object_cls.__name__))

        if value._hive_object_cls is not self._hive_object_cls:
            raise AttributeError("HiveInternals (ex) attribute '%s' cannot contain a Bee built by a different hive" %
                                 name)

        self._bee_names.add(name)
        value._hive_bee_name = name

        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name not in self._bee_names:
            raise AttributeError("HiveInternals (ex) has no attribute '%s" % name)

        self._bee_names.remove(name)
        object.__delattr__(self, name)

    def __dir__(self):
        return self._bee_names

    def __iter__(self):
        return iter(self._bee_names)
