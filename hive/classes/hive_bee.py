from .. import get_building_hive
from ..mixins import Bee
from .. import manager


class HiveBee(Bee):
    # TODO: resolve method for arguments that are bees (returns a new HiveBee class?)

    def __init__(self, cls, *args, **kwargs):
        self._hivecls = get_building_hive()
        assert get_building_hive() is not None
        assert cls is None or callable(cls), cls 
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    @manager.getinstance    
    def getinstance(self, hiveobject):        
        assert callable(self.cls), self.cls
        return self.cls(*self.args, **self.kwargs)
