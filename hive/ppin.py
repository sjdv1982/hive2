from .mixins import Antenna, Output, Stateful, ConnectTarget, TriggerSource, TriggerTarget, Bee, Bindable, Callable
from .classes import HiveBee, Pusher
from .manager import get_mode, get_building_hive, memoize


def compare_types(b1, b2):
    for t1, t2 in zip(b1.data_type, b2.data_type):
        if t1 != t2:
            raise TypeError((b1.data_type, b2.data_type)) # TODO: nice error message


class PPInBase(Antenna, ConnectTarget, TriggerSource, Bindable):
    def __init__(self, target, data_type, bound=False, run_hive=None):
        assert isinstance(target, Stateful) or target.implements(Callable), target
        self._stateful = isinstance(target, Stateful)
        self.target = target
        self.data_type = data_type
        self._bound = bound
        self._run_hive = run_hive
        self._trigger = Pusher(self)
        self._pretrigger = Pusher(self)
                
    def _hive_trigger_source(self, targetfunc):
        self._trigger.add_target(targetfunc)

    def _hive_pretrigger_source(self, targetfunc):
        self._pretrigger.add_target(targetfunc)
                
    @memoize
    def bind(self, run_hive):
        self._run_hive = run_hive
        if self._bound:
            return self

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(run_hive)

        return self.__class__(target, self.data_type, bound=True, run_hive=run_hive)


class PushIn(PPInBase):
    mode = "push"

    def push(self, value):
        # TODO: exception handling hooks
        self._pretrigger.push()

        if self._stateful:
            self.target._hive_stateful_setter(self._run_hive, value)

        else:
            self.target(value)

        self._trigger.push()

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
        self._pretrigger.push()
        value = self._pull_callback()

        if self._stateful:
            self.target._hive_stateful_setter(self._run_hive, value)

        else:
            self.target(value)

        self._trigger.push()

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
            self.data_type = target.data_type

        else:
            self.data_type = ()

        self._hive_cls = get_building_hive()
        self.target = target

    @memoize
    def getinstance(self, hive_object):
        target = self.target

        if isinstance(target, Bee): 
            target = target.getinstance(hive_object)

        if self.mode == "push":    
            return PushIn(target, self.data_type)

        return PullIn(target, self.data_type)

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
