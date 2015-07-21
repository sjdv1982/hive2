from .hive import HiveMethodWrapper
from .mixins import Stateful, Exportable, Bindable
from .tuple_type import tuple_type
from .manager import get_mode, get_building_hive, memoize
from weakref import WeakSet


class Property(Stateful, Bindable, Exportable):
    """Interface to bind class attributes"""

    def __init__(self, cls, attr, data_type, start_value):
        self._hive_cls = get_building_hive()
        self._cls = cls
        self._attr = attr
        self._bound = WeakSet()

        self.data_type = data_type
        self.start_value = start_value

    def _hive_stateful_getter(self, run_hive):
        cls = self._cls

        assert cls in run_hive._hive_build_class_instances, cls
        instance = run_hive._hive_build_class_instances[cls]

        return getattr(instance, self._attr)

    def _hive_stateful_setter(self, run_hive, value):
        cls = self._cls

        assert cls in run_hive._hive_build_class_instances, cls
        instance = run_hive._hive_build_class_instances[cls]

        setattr(instance, self._attr, value)

    def export(self):
        return self

    @memoize
    def bind(self, run_hive):
        self._bound.add(run_hive)
        
        cls = self._cls
        assert cls in run_hive._hive_build_class_instances, cls
        instance = run_hive._hive_build_class_instances[cls]

        if self.start_value is not None or not hasattr(instance, self._attr):
            setattr(instance, self._attr, self.start_value)

        return self


def property(cls, attr, data_type=None, start_value=None):
    data_type = tuple_type(data_type)

    if get_mode() == "immediate":
        raise ValueError("hive.property cannot be used in immediate mode")

    else:
        assert isinstance(cls, HiveMethodWrapper), "hive.property(cls) must be the cls argument in" \
                                                   " build(cls, i, ex, args)"
        return Property(cls._cls, attr, data_type, start_value)