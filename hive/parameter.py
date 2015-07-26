from .mixins import Antenna, Exportable
from .manager import get_building_hive, ContextFactory


class Parameter(Antenna, Exportable):

    def __init__(self, target):
        assert isinstance(target, Antenna), target
        self._hive_cls = get_building_hive()
        self._target = target

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target

        if isinstance(target, Exportable):
            target = target.export()

        return target


parameter = ContextFactory("hive.parameter", deferred_cls=Parameter)
