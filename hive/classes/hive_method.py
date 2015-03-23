from ..mixins import Bindable, Callable, Exportable
from .. import get_building_hive
from .. import manager
import functools


class Method(Bindable, Callable, Exportable):

    def __init__(self, func): 
        self._hive_cls = get_building_hive()
        # TODO support py3 here
        assert hasattr(func, "im_class"), func #must be a method
        self._func = func

    @manager.bind
    def bind(self, run_hive):
        cls = self._func.im_class
        assert id(cls) in run_hive._hive_buildclass_instances, cls
        instance = run_hive._hive_buildclass_instances[id(cls)]
        return functools.partial(self._func, instance)

    def export(self):
        return self