from ..mixins import Bindable, Callable, Exportable
from ..manager import get_building_hive, memoize


class Method(Bindable, Callable, Exportable):

    def __init__(self, builder_cls, func):
        self._builder_cls = builder_cls
        self._func = func
        self._hive_cls = get_building_hive()

    @memoize
    def bind(self, run_hive):
        cls = self._builder_cls
        instance = run_hive._hive_build_class_instances[cls]

        return self._func.__get__(instance)

    def export(self):
        return self