from .mixins import Bee, ConnectSource, TriggerSource, Exportable
from . import get_mode, get_building_hive


class Hook(Exportable, Bee):

    def __init__(self, target):
        assert isinstance(target, TriggerSource), target
        self._hivecls = get_building_hive()
        self._target = target

    def export(self):
        #TODO: somehow log the redirection path
        t = self._target
        if isinstance(t, Exportable):
            t = t.export()

        return t    


def hook(target):
    if get_mode() == "immediate":
        raise ValueError("hive.hook cannot be used in immediate mode")

    else:
        return Hook(target)