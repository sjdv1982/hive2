from ..mixins import Bee, Bindable
from ..manager import memoize


class BindableResolveBee(Bee, Bindable):

    def __init__(self, unbound_run_hive, bee):
        self._bee = bee
        self._unbound_run_hive = unbound_run_hive
        self._hive_object = unbound_run_hive._hive_object

    @memoize
    def bind(self, run_hive):
        hive_instance = self._unbound_run_hive.bind(run_hive)
        return self._bee.bind(hive_instance)


class ResolveBee(Bee):
    """Wraps Bee instance to resolve appropriate reference at runtime"""

    def __init__(self, bee, own_hive_object):
        self._bee = bee
        self._own_hive_object = own_hive_object

    def __getattr__(self, attr):
        result = getattr(self._bee, attr)

        # Return qualified resolve bee (replace child bee hiveobject with this resolution)
        if isinstance(result, ResolveBee):
            child_bee = ResolveBee(result._bee, self)
            return child_bee

        return result

    def __repr__(self):
        return "<*{}::{}>".format(self._own_hive_object, self._bee)

    @memoize
    def getinstance(self, hive_object):
        unbound_run_hive = self._own_hive_object.getinstance(hive_object)
        hive_object = unbound_run_hive._hive_object

        result = self._bee.getinstance(hive_object)

        if isinstance(result, Bindable):
            return BindableResolveBee(unbound_run_hive, result)

        return result

    def implements(self, cls):
        return self._bee.implements(cls)