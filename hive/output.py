from .mixins import Output, Exportable
from .manager import ContextFactory, get_building_hive


class HiveOutput(Output, Exportable):

    def __init__(self, target):
        assert isinstance(target, Output), target
        self._hive_cls = get_building_hive()
        self._target = target

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            target = target.export()

        return target


output = ContextFactory("hive.output", immediate_cls=None, deferred_cls=HiveOutput)