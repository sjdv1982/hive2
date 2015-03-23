from ..mixins import Bee, Exportable
from ..hive import HiveObject


class HiveInternals(object):

    def __init__(self, hivecls):
        assert hivecls is not None
        self._hivecls = hivecls
        self._attrs = []

    def __setattr__(self, name, value):
        if name == "parent":
            raise AttributeError("HiveInternals (i) special attribute 'parent' cannot be assigned to" % value.__class__)

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        if value is None:
            if hasattr(self, name):
                self.__delattr__(name)

            return

        if not isinstance(value, Bee):
            raise TypeError("HiveInternals (i) attribute '%s' must be a Bee, not '%s'" % (name,    value.__class__))

        if isinstance(value, Exportable) and not isinstance(value, HiveObject):
            raise TypeError("HiveInternals (i) attribute '%s' must not be Exportable; Exportables must be added to ex"
                            % name)

        if value._hive_cls is None:
            raise AttributeError("HiveInternals (i) attribute '%s' must contain a Bee built by '%s' (or one of its base"
                                 " classes), but the Bee was not built by any hive" % (name, self._hivecls.__name__))

        if not issubclass(value._hive_cls, self._hivecls):
            raise AttributeError("HiveInternals (i) attribute '%s' must contain a Bee built by '%s' (or one of its base"
                                 " classes), not '%s'" % (name, self._hivecls.__name__, value._hive_cls.__name__))

        if name not in self._attrs:
            self._attrs.append(name)

        object.__setattr__(self, name, value)

    def __delattr__(self, attr):
        if attr not in self._attrs:
            raise AttributeError

        self._attrs.remove(attr)
        object.__delattr__(self, attr)

    def __dir__(self):
        return list(self._attrs)
