from .mixins import Bee, TriggerTarget, Exportable
from .manager import get_building_hive, ContextFactory


class Entry(Exportable, Bee):
    """Exportable proxy for TriggerTarget bees"""

    def __init__(self, target):
        assert isinstance(target, Bee), target
        assert target.implements(TriggerTarget)

        self._hive_object_cls = get_building_hive()
        self._target = target

    def __repr__(self):
        return "<{}: {}>".format(self.__class__.__name__, self._target)

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            target = target.export()

        return target


entry = ContextFactory("hive.entry", build_mode_cls=Entry)