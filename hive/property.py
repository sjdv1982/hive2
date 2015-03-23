from .hive import HiveMethodWrapper
from .mixins import Stateful, Exportable, Bindable
from . import get_mode, get_building_hive


def tupletype(t):
    if t is None:
        return ()

    if isinstance(t, str):
        return (t,)

    assert isinstance(t, tuple), t
    
    def _check_tupletype(t):
        if isinstance(t, str):
            return

        assert isinstance(t, tuple), t
        for tt in t:
            _check_tupletype(tt)
    
    _check_tupletype(t)
    return t


class Property(Stateful, Bindable, Exportable):

    def __init__(self, cls, attr, datatype, startvalue): 
        self._hivecls = get_building_hive()
        self._cls = cls
        self._attr = attr
        self.datatype = datatype
        self.startvalue = startvalue

    def _hive_stateful_getter(self, runhive):
        cls = self._cls
        assert id(cls) in runhive._hive_buildclass_instances, cls
        instance = runhive._hive_buildclass_instances[id(cls)]        
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
        if self.startvalue is not None or not hasattr(instance, self._attr):
            setattr(instance, self._attr, self.startvalue)

        return self


def property(cls, attr, datatype=None, startvalue=None): 
    datatype = tupletype(datatype)
    if get_mode() == "immediate":
        raise ValueError("hive.property cannot be used in immediate mode")

    else:
        assert isinstance(cls, HiveMethodWrapper) #property(cls) must be the cls argument in build(cls, i, ex, args)
        return Property(cls._cls, attr, datatype, startvalue) 