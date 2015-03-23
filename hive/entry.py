from .mixins import Bee, ConnectTarget, TriggerTarget, Exportable
from . import get_building_hive
from .context_factory import ContextFactory


class Entry(Exportable, Bee):

    def __init__(self, target):
        assert isinstance(target, TriggerTarget), target
        self._hivecls = get_building_hive()
        self._target = target

    def export(self):
        #TODO: somehow log the redirection path
        t = self._target
        if isinstance(t, Exportable):
            t = t.export()
        return t    


entry = ContextFactory("hive.entry", deferred_cls=Entry)