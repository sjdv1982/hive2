from . import SPECIAL_NAMES
from ..mixins import Bee, Exportable


class HiveExportables(object):

    def __init__(self, hive_cls):
        assert hive_cls is not None
        self._hive_object_cls = hive_cls

        self._bee_names = set()
        self._ordered_bee_names = []

    def __setattr__(self, name, value):
        if name in SPECIAL_NAMES:
            raise AttributeError("HiveExportables (ex) special attribute '{}' cannot be assigned to".format(name))

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        if value is None:
            if hasattr(self, name):
                self.__delattr__(name)

            return

        if not isinstance(value, Bee):
            raise TypeError("HiveExportables (i) attribute '{}' must be a Bee, not '{}'"
                            .format((name, value.__class__)))

        if not isinstance(value, Exportable):
            raise TypeError("HiveExportables (ex) attribute must be an Exportable, not '%s'".format(value.__class__))

        if value._hive_object_cls is None:
            raise AttributeError("HiveExportables (ex) attribute '%s' must contain a Bee built by '%s' (or one of its b"
                                 "ase classes), but the Bee was not built by any hive"
                                 .format(name, self._hive_object_cls.__name__))

        if value._hive_object_cls is not self._hive_object_cls:
            raise AttributeError("HiveExportables (ex) attribute '%s' cannot contain a Bee built by a different hive"
                                 .format(name))

        if name not in self._bee_names:
            self._bee_names.add(name)
            self._ordered_bee_names.append(name)

        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name not in self._bee_names:
            raise AttributeError

        self._bee_names.remove(name)
        self._ordered_bee_names.remove(name)

        object.__delattr__(self, name)

    def __bool__(self):
        return bool(self._ordered_bee_names)

    def __dir__(self):
        return self._ordered_bee_names

    def __iter__(self):
        return iter(self._ordered_bee_names)

    def __repr__(self):
        member_pairs = ("{} = {}".format(k, getattr(self, k)) for k in self._ordered_bee_names)
        return "<HiveExportables (ex)>\n\t{}".format("\n\t".join(member_pairs))
