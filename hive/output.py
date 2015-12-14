from .manager import ContextFactory, get_building_hive, memoize
from .mixins import Output, Exportable, Bee


class HiveOutput(Output, Exportable):
    """Exportable proxy for Output bees"""

    def __init__(self, target):
        assert isinstance(target, Bee), target
        assert target.implements(Output)
        self._hive_object_cls = get_building_hive()
        self._target = target

    def __repr__(self):
        return "<Output: {}::{}>".format(self._hive_object_cls, self._target)

    @memoize
    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            target = target.export()

        return target


output = ContextFactory("hive.output", build_mode_cls=HiveOutput)