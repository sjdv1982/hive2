from ..mixins import Bindable, Callable, Exportable
from .. import get_building_hive
from .. import manager
import functools


class Method(Bindable, Callable, Exportable):

    def __init__(self, func): 
        self._hivecls = get_building_hive()
        # TODO support py3 here
        assert hasattr(func, "im_class"), func #must be a method
        self._func = func

    @manager.bind
    def bind(self, runhive):
        cls = self._func.im_class
        assert id(cls) in runhive._hive_buildclass_instances, cls
        instance = runhive._hive_buildclass_instances[id(cls)]
        return functools.partial(self._func, instance)

    def export(self):
        return self