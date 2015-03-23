from ..mixins import Bee, Bindable


class ResolveBee(Bee):
    """Wraps Bee instance to resolve appropriate reference at runtime"""

    def __init__(self, bee, ownhiveobject):
        self._bee = bee
        self._ownhiveobject = ownhiveobject

    def __getattr__(self, attr):
        return getattr(self._bee, attr)

    def getinstance(self, hiveobject): 
        hive_instance = self._ownhiveobject.getinstance(hiveobject)
        result = self._bee.getinstance(hive_instance._hive_object)

        if isinstance(result, Bindable):
            result = result.bind(hive_instance)

        return result

    def implements(self, cls):
        return self._bee.implements(cls)