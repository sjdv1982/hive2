from ..mixins import Bindable, Callable, Exportable
from .. import get_building_hive
from .. import manager

import functools


class Method(Bindable, Callable, Exportable):

    def __init__(self, builder_cls, func):
        self._builder_cls = builder_cls
        self._func = func
        self._hive_cls = get_building_hive()

    @manager.bind
    def bind(self, run_hive):
        cls = self._builder_cls
        instance = run_hive._hive_build_class_instances[cls]
        return functools.partial(self._func, instance)

    def export(self):
        return self