from .mixins import Bee, TriggerSource, Exportable
from .manager import get_building_hive, ContextFactory


class Hook(Exportable, Bee):
    """Exportable proxy for TriggerSource bees"""

    def __init__(self, target):
        assert isinstance(target, TriggerSource), target
        self._hive_object_cls = get_building_hive()
        self._target = target

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            target = target.export()

        return target


hook = ContextFactory("hive.hook", build_mode_cls=Hook)