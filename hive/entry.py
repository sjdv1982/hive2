from .mixins import Bee, ConnectTarget, TriggerTarget, Exportable
from . import get_building_hive
from .context_factory import ContextFactory


class Entry(Exportable, Bee):
    """Exportable proxy for TriggerTarget bees"""

    def __init__(self, target):
        assert isinstance(target, TriggerTarget), target
        self._hive_cls = get_building_hive()
        self._target = target

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            target = target.export()

        return target


entry = ContextFactory("hive.entry", deferred_cls=Entry)