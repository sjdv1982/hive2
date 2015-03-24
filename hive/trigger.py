from .mixins import TriggerSource, TriggerTarget, Bee, Bindable
from .classes import HiveBee
from . import get_mode
from . import manager
from .hive import HiveObject


def build_trigger(source, target, pre):
    # TODO: register connection, or insert a listener function in between
    target_func = target._hive_trigger_target()

    if pre:
        source._hive_pretrigger_source(target_func)

    else:
        source._hive_trigger_source(target_func)


class Trigger(Bindable):

    def __init__(self, source, target, pretrigger):
        self.source = source
        self.target = target
        self.pretrigger = pretrigger

    @manager.bind
    def bind(self, run_hive):
        source = self.source
        if isinstance(source, Bindable):
            source = source.bind(run_hive)

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(run_hive)

        return build_trigger(source, target, self.pretrigger)


class TriggerBee(HiveBee):

    def __init__(self, source, target, pretrigger):
        HiveBee.__init__(self, None, source, target, pretrigger)

    @manager.getinstance
    def getinstance(self, hive_object):
        source, target, pretrigger = self.args

        if isinstance(source, HiveObject):
            source = source.get_trigger_source()

        if isinstance(source, Bee):
            source = source.getinstance(hive_object)

        if isinstance(target, HiveObject):
            target = target.get_trigger_target()

        if isinstance(target, Bee):    
            target = target.getinstance(hive_object)

        if get_mode() == "immediate":            
            return build_trigger(source, target, pretrigger)

        else:
            return Trigger(source, target, pretrigger)


def _trigger(source, target, pretrigger):
    if isinstance(source, Bee):
        assert source.implements(TriggerSource), source
        assert target.implements(TriggerTarget), target

    else:
        assert isinstance(source, TriggerSource), source
        assert isinstance(target, TriggerTarget), target

    if get_mode() == "immediate":
        build_trigger(source, target,pretrigger)

    else:
        trigger_bee = TriggerBee(source, target, pretrigger)
        manager.register_bee(trigger_bee)
        return trigger_bee


def trigger(source, target, pretrigger=False):
    return _trigger(source, target, pretrigger)
