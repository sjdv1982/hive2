from ..method import Method
from ..property import Property

from ..annotations import get_argument_options, get_return_type
from ..compatability import is_method
from ..identifiers import identifier_to_tuple


class HiveClassProxy(object):
    """Intercept attribute lookups to return wrapped methods belonging to a given class."""

    def __init__(self, cls):
        object.__setattr__(self, "_cls", cls)

    def __getattr__(self, attr):
        value = getattr(self._cls, attr)

        if is_method(value):
            return Method(self._cls, value)

        elif isinstance(value, property):
            return self._property_from_descriptor(attr, value)

        else:
            return value

    def __setattr__(self, attr):
        raise AttributeError("HiveMethodWrapper of class '{}' is read-only".format(self._cls.__name__))

    def __repr__(self):
        self_cls = object.__getattribute__(self, "__class__")
        wrapped_cls = object.__getattribute__(self, "_cls")
        return "{}({})".format(self_cls.__name__, wrapped_cls)

    def _property_from_descriptor(self, attr, prop):
        """Create a hive.property object from descriptor"""
        raw_getter_type = get_return_type(prop.fget)
        data_type = identifier_to_tuple(raw_getter_type)

        if prop.fset is not None:
            raw_setter_type = next(iter(get_argument_options(prop.fset)))
            if identifier_to_tuple(raw_setter_type) != raw_getter_type:
                raise TypeError()

        return Property(self._cls, attr, data_type, None)