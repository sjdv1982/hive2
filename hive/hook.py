from .context_factory import ContextFactory
from .mixins import Bee, TriggerSource, Exportable
from . import get_building_hive


class Hook(Exportable, Bee):

    def __init__(self, target):
        assert isinstance(target, TriggerSource), target
        self._hive_cls = get_building_hive()
        self._target = target

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            target = target.export()

        return target


hook = ContextFactory("hive.hook", deferred_cls=Hook)