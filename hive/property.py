from .hive import HiveMethodWrapper
from .mixins import Stateful, Exportable, Bindable
from . import get_mode, get_building_hive


def _check_tuple_type(value):
    if isinstance(value, str):
        return

    assert isinstance(value, tuple), value
    for entry in value:
        _check_tuple_type(entry)


def tuple_type(value):
    if value is None:
        return ()

    if isinstance(value, str):
        return (value,)
    
    _check_tuple_type(value)
    return value


class Property(Stateful, Bindable, Exportable):

    def __init__(self, cls, attr, data_type, start_value):
        self._hive_cls = get_building_hive()
        self._cls = cls
        self._attr = attr

        self.data_type = data_type
        self.start_value = start_value

    def _hive_stateful_getter(self, run_hive):
        cls = self._cls
        assert id(cls) in run_hive._hive_buildclass_instances, cls
        instance = run_hive._hive_buildclass_instances[id(cls)]
        return getattr(instance, self._attr)

    def _hive_stateful_setter(self, runhive, value):
        cls = self._cls
        assert id(cls) in runhive._hive_buildclass_instances, cls
        instance = runhive._hive_buildclass_instances[id(cls)]                
        setattr(instance, self._attr, value)

    def export(self):
        return self

    def bind(self, runhive):
        cls = self._cls
        assert id(cls) in runhive._hive_buildclass_instances, cls
        instance = runhive._hive_buildclass_instances[id(cls)]
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