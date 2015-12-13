from functools import partial

from .classes import Pusher
from .manager import get_mode, get_building_hive, memoize
from .mixins import Antenna, Output, Stateful, ConnectTarget, TriggerSource, TriggerTarget, Bee, Bindable, Callable
from .tuple_type import types_match


class PPInBase(Antenna, ConnectTarget, TriggerSource, Bindable):

    def __init__(self, target, data_type=None, bound=None, run_hive=None):
        # Once bound, hive Method object is resolved to a function, not bee
        assert isinstance(target, Stateful) or isinstance(target, Callable) or callable(target), target

        if isinstance(target, Stateful):
            data_type = target.data_type
            self._set_value = partial(target._hive_stateful_setter, run_hive)
        else:
            self._set_value = target

        self.target = target
        self.data_type = data_type
        self._bound = bound
        self._run_hive = run_hive
        self._trigger = Pusher(self)
        self._pretrigger = Pusher(self)
                
    def _hive_trigger_source(self, func):
        self._trigger.add_target(func)

    def _hive_pretrigger_source(self, func):
        self._pretrigger.add_target(func)
                
    @memoize
    def bind(self, run_hive):
        if self._bound:
            return self

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(run_hive)

        return self.__class__(target, self.data_type, bound=run_hive, run_hive=run_hive)


class PushIn(PPInBase):
    mode = "push"

    def push(self, value):
        # TODO: exception handling hooks
        self._pretrigger.push()

        self._set_value(value)

        self._trigger.push()

    def _hive_is_connectable_target(self, source):
        if not isinstance(source, Output):
            raise TypeError("Source {} does not implement Output".format(source))

        if source.mode != "push":
            raise TypeError("Source {} is not configured for push mode".format(source))

        if not types_match(source.data_type, self.data_type, allow_none=True):
            raise TypeError("Data types do not match: {}, {}".format(source.data_type, self.data_type))

    def _hive_connect_target(self, source):
        pass        
            

class PullIn(PPInBase, TriggerTarget):
    mode = "pull"
    _pull_callback = None

    def pull(self):
        # TODO: exception handling hooks
        self._pretrigger.push()
        value = self._pull_callback()

        self._set_value(value)

        self._trigger.push()

    def _hive_is_connectable_target(self, source):
        if not isinstance(source, Output):
            raise TypeError("Source {} does not implement Output".format(source))

        if source.mode != "pull":
            raise TypeError("Source {} is not configured for pull mode".format(source))

        if not types_match(source.data_type, self.data_type, allow_none=True):
            raise TypeError("Data types do not match")

    def _hive_connect_target(self, source):
        if self._pull_callback is not None:
            raise TypeError("pull_in cannot accept more than one connection: {}".format(source))

        self._pull_callback = source.pull
    
    def _hive_trigger_target(self):
        return self.pull

    __call__ = pull


class PPInBee(Antenna, ConnectTarget, TriggerSource):
    mode = None

    def __init__(self, target):
        is_stateful = isinstance(target, Stateful)

        if not (is_stateful or target.implements(Callable)):
            raise TypeError("Target must implement Callable or Stateful protocol")

        if is_stateful:
            self.data_type = target.data_type

        else:
            self.data_type = None

        self._hive_object_cls = get_building_hive()
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
        if Bee.implements(self, cls):
            return True

        target = self.target
        if isinstance(target, Bee):
            return target.implements(cls)

        return False
    
    
class PushInBee(PPInBee):
    mode = "push"


class PullInBee(PPInBee, TriggerTarget):
    mode = "pull"


def push_in(target):
    if get_mode() == "immediate":
        return PushIn(target)

    else:
        return PushInBee(target)


def pull_in(target):
    if get_mode() == "immediate":
        return PullIn(target)

    else:
        return PullInBee(target)
