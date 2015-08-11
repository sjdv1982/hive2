from .mixins import Bee, Antenna, Exportable
from .manager import get_building_hive, ContextFactory


class HiveAntenna(Antenna, Exportable):

    def __init__(self, target):
        assert isinstance(target, Bee), target
        assert target.implements(Antenna)

        self._hive_object_cls = get_building_hive()
        self._target = target

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target

        if isinstance(target, Exportable):
            target = target.export()

        return target


antenna = ContextFactory("hive.antenna", build_mode_cls=HiveAntenna)
