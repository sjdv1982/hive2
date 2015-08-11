from weakref import WeakKeyDictionary

from .mixins import Stateful, Bindable, Bee
from .manager import ContextFactory, get_building_hive, memoize
from .tuple_type import tuple_type


class Variable(Stateful, Bindable, Bee):
    """A non-exportable Attribute type"""

    def __init__(self, data_type=None, start_value=None):
        self._hive_object_cls = get_building_hive()

        self.data_type = tuple_type(data_type)
        self.start_value = start_value

        self._values = WeakKeyDictionary()

    def _hive_stateful_getter(self, run_hive):
        return self._values[run_hive]

    def _hive_stateful_setter(self, run_hive, value):
        assert run_hive in self._values, run_hive
        self._values[run_hive] = value

    @memoize
    def bind(self, run_hive):
        self._values[run_hive] = self.start_value
        return self


variable = ContextFactory("hive.variable", build_mode_cls=Variable)
