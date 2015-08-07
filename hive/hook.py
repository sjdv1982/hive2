from .mixins import Bee, TriggerSource, Exportable
from .manager import get_building_hive, ContextFactory


class Hook(Exportable, Bee):
    """Exportable proxy for TriggerSource bees"""

    def __init__(self, target):
        assert isinstance(target, Bee), target
        assert target.implements(TriggerSource)
        self._hive_object_cls = get_building_hive()
        self._target = target

    def __repr__(self):
        return "<Hook"

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target

        if target.implements(Exportable):
            target = target.export()

        return target


hook = ContextFactory("hive.hook", build_mode_cls=Hook)