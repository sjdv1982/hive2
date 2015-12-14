from weakref import WeakKeyDictionary

from .manager import ContextFactory, get_building_hive, memoize
from .mixins import Stateful, Exportable, Bindable, Parameter
from .tuple_type import tuple_type


class Attribute(Stateful, Bindable, Exportable):
    """Stateful data store object"""

    export_only = False

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

    def export(self):
        return self

    @memoize
    def bind(self, run_hive):
        start_value = self.start_value

        if isinstance(start_value, Parameter):
            start_value = start_value.get_runtime_value(run_hive)

        self._values[run_hive] = start_value
        return self


attribute = ContextFactory("hive.attribute", build_mode_cls=Attribute)
