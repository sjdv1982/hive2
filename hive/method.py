from hive.mixins import Bindable, Callable, Exportable
from hive.manager import get_building_hive, memoize
from hive.annotations import update_wrapper


class Method(Bindable, Callable, Exportable):
    """Exportable interface to instance methods of bind classes"""

    def __init__(self, builder_cls, func):
        self._builder_cls = builder_cls
        self._func = func
        self._hive_object_cls = get_building_hive()

        update_wrapper(self, func)

    def __repr__(self):
        return "<{}: {}>".format(self.__name__, self._func.__qualname__)

    @memoize
    def bind(self, run_hive):
        cls = self._builder_cls
        instance = run_hive._hive_build_class_instances[cls]

        return self._func.__get__(instance)

    def export(self):
        return self