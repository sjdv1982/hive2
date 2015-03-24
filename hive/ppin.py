from .mixins import Antenna, Output, Stateful, ConnectTarget, TriggerSource, TriggerTarget, Bee, Bindable, Callable
from .classes import HiveBee, Pusher
from . import get_mode, get_building_hive
from . import manager


def compare_types(b1, b2):
    for t1, t2 in zip(b1.datatype, b2.datatype):
        if t1 != t2:
            raise TypeError((b1.datatype, b2.datatype)) # TODO: nice error message


class PPInBase(Antenna, ConnectTarget, TriggerSource, Bindable):
    def __init__(self, target, datatype, bound=False, run_hive=None):
        assert isinstance(target, Stateful) or target.implements(Callable), target
        self._stateful = isinstance(target, Stateful)
        self.target = target
        self.datatype = datatype
        self._bound = bound
        self._run_hive = run_hive
        self._trig = Pusher(self)
        self._pretrig = Pusher(self)        
                
    def _hive_trigger_source(self, targetfunc):
        self._trig.add_target(targetfunc)

    def _hive_pretrigger_source(self, targetfunc):
        self._pretrig.add_target(targetfunc)
                
    @manager.bind
    def bind(self, run_hive):
        self._run_hive = run_hive
        if self._bound:
            return self

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(run_hive)

        return self.__class__(target, self.datatype, bound=True, run_hive=run_hive)

class PushIn(PPInBase):
    mode = "push"

    def push(self, value):
        # TODO: exception handling hooks
        self._pretrig.push()

        if self._stateful:
            self.target._hive_stateful_setter(self._run_hive, value)

        else:
            self.target(value)

        self._trig.push()

    def _hive_connectable_target(self, source):
        assert isinstance(source, Output) # TODO : nicer error message
        assert source.mode == "push" # TODO : nicer error message
        compare_types(source, self)

    def _hive_connect_target(self, source):
        pass        
            

class PullIn(PPInBase, TriggerTarget):
    mode = "pull"
    _pull_callback = None

    def __call__(self):
        self.pull()

    def pull(self):
        # TODO: exception handling hooks
        self._pretrig.push()
        value = self._pull_callback()

        if self._stateful:
            self.target._hive_stateful_setter(self._run_hive, value)

        else:
            self.target(value)

        self._trig.push()

    def _hive_connectable_target(self, source):
        assert isinstance(source, Output) # TODO : nicer error message
        assert source.mode == "pull" # TODO : nicer error message
        compare_types(source, self)

    def _hive_connect_target(self, source):
        if self._pull_callback is not None:
            raise TypeError("PullIn cannot accept more than one connection") # TODO: nicer error message, with names

        self._pull_callback = source.pull
    
    def _hive_trigger_target(self):
        return self.pull


class PPInBee(Antenna, ConnectTarget, TriggerSource):
    mode = None

    def __init__(self, target):        
        assert isinstance(target, Stateful) or isinstance(target, Antenna) or target.implements(Callable) # TODO: nice error message
        if isinstance(target, Stateful) or isinstance(target, Antenna):
            self.datatype = target.datatype

        else:
            self.datatype = ()

        self._hive_cls = get_building_hive()
        self.target = target

    @manager.getinstance
    def getinstance(self, hiveobject):        
        target = self.target

        if isinstance(target, Bee): 
            target = target.getinstance(hiveobject)

        if self.mode == "push":    
            ret = PushIn(target, self.datatype)

        else:
            ret = PullIn(target, self.datatype)

        return ret

    def implements(self, cls):
        if isinstance(self, cls):
            return True

        target = self.target
        if isinstance(target, Bee):
            return target.implements(cls)

        return False
    
    
class PushInBee(PPInBee):
    mode = "push"


class PullInBee(PPInBee, TriggerTarget):
    mode = "pull"


def pushin(target):
    assert isinstance(target, Stateful) or isinstance(target, Antenna) or target.implements(Callable) # TODO: nice error message
    if get_mode() == "immediate":
        return PushIn(target)

    else:
        return PushInBee(target)


def pullin(target):
    assert isinstance(target, Stateful) or isinstance(target, Antenna) or target.implements(Callable) # TODO: nice error message
    if get_mode() == "immediate":
        return PullIn(target)

    else:
        return PullInBee(target)
