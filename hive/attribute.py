from weakref import WeakKeyDictionary

from .mixins import Stateful, Exportable, Bindable
from .manager import ContextFactory, get_building_hive


class Attribute(Stateful, Bindable, Exportable):

    def __init__(self, data_type=None, start_value=None):
        self._hive_cls = get_building_hive()

        self.data_type = data_type
        self.start_value = start_value

        self._values = WeakKeyDictionary()

    def _hive_stateful_getter(self, run_hive):
        return self._values[run_hive]

    def _hive_stateful_setter(self, run_hive, value):
        assert run_hive in self._values, run_hive
        self._values[run_hive] = value
        
    def export(self):
        return self

    def bind(self, run_hive):
        if run_hive in self._values:
            return

        self._values[run_hive] = self.start_value
        return self


attribute = ContextFactory("hive.attribute", deferred_cls=Attribute)
