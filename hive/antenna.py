from .manager import get_building_hive, ContextFactory
from .mixins import Bee, Antenna, Exportable


class HiveAntenna(Antenna, Exportable):
    """Exportable proxy for Antenna bees"""

    def __init__(self, target):
        assert isinstance(target, Bee), target
        assert target.implements(Antenna)

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


antenna = ContextFactory("hive.antenna", build_mode_cls=HiveAntenna)
