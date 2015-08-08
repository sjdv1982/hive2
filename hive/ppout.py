from .mixins import Antenna, Output, Stateful, Bee, Bindable, Exportable, Callable, ConnectSource, ConnectTarget, \
    TriggerSource, TriggerTarget, Socket, Plugin
from .classes import HiveBee, Pusher
from .manager import get_mode, get_building_hive, memoize
from .tuple_type import types_match


class PPOutBase(Output, ConnectSource, TriggerSource, Bindable):
    def __init__(self, target, data_type, bound=None, run_hive=None):
        if not bound:
            assert isinstance(target, Stateful) or target.implements(Callable), target

        self._stateful = isinstance(target, Stateful)
        self.target = target
        self.data_type = data_type
        self._bound = bound
        self._run_hive = run_hive
        self._trigger = Pusher(self)
        self._pretrigger = Pusher(self)
                
    @memoize
    def bind(self, run_hive):
        if self._bound:
            return self

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(run_hive)

        return self.__class__(target, self.data_type, bound=run_hive, run_hive=run_hive)

    def _hive_trigger_source(self, func):
        self._trigger.add_target(func)

    def _hive_pretrigger_source(self, func):
        self._pretrigger.add_target(func)


class PullOut(PPOutBase):
    mode = "pull"

    def pull(self):
        # TODO: exception handling hooks
        self._pretrigger.push()
        if self._stateful:
            value = self.target._hive_stateful_getter(self._run_hive)

        else:
            value = self.target()

        self._trigger.push()
        return value

    def _hive_is_connectable_source(self, target):
        # TODO what if already connected
        if not isinstance(target, Antenna):
            raise TypeError("Target {} does not implement Antenna".format(target))

        if target.mode != "pull":
            raise TypeError("Target {} is not configured for pull mode".format(target))

        if not types_match(target.data_type, self.data_type, allow_none=True):
            raise TypeError("Data types do not match")

    def _hive_connect_source(self, target):
        pass

    
class PushOut(PPOutBase, Socket, ConnectTarget, TriggerTarget):
    mode = "push"

    def __init__(self, target, data_type, bound=None, run_hive=None):
        PPOutBase.__init__(self, target, data_type, bound, run_hive)
        self._targets = []

    def __call__(self):
        self.push()

    def push(self):
        # TODO: exception handling hooks
        self._pretrigger.push()

        if self._stateful:
            value = self.target._hive_stateful_getter(self._run_hive)

        else:
            value = self.target()

        for target in self._targets:
            target(value)

        self._trigger.push()

    def socket(self):
        return self.push
    
    def _hive_is_connectable_source(self, target):
        if not isinstance(target, Antenna):
            raise TypeError("Target {} does not implement Antenna".format(target))

        if target.mode != "push":
            raise TypeError("Target {} is not configured for push mode".format(target))

        if not types_match(target.data_type, self.data_type, allow_none=True):
            raise TypeError("Data types do not match")
    
    def _hive_connect_source(self, target):
        self._targets.append(target.push)
            
    def _hive_is_connectable_target(self, source):
        if not isinstance(source, Plugin):
            raise TypeError("Source does not implement Plugin: {}".format(source))

    def _hive_connect_target(self, source):
        self._targets.append(source.plugin)
            
    def _hive_trigger_target(self):
        return self.push


class PPOutBee(Output, ConnectSource, TriggerSource):
    mode = None

    def __init__(self, target):        
        assert isinstance(target, Stateful) or isinstance(target, Output) or target.implements(Callable) # TODO: nice error message
        if isinstance(target, Stateful) or isinstance(target, Output):
            self.data_type = target.data_type

        else:
            self.data_type = ()

        self._hive_object_cls = get_building_hive()
        self.target = target

    @memoize
    def getinstance(self, hive_object):
        target = self.target

        if isinstance(target, Bee): 
            target = target.getinstance(hive_object)

        if self.mode == "push":    
            instance = PushOut(target, self.data_type)

        else:
            instance = PullOut(target, self.data_type)

        return instance

    def implements(self, cls):
        if Bee.implements(self, cls):
            return True

        target = self.target
        if isinstance(target, Bee):
            return target.implements(cls)

        return False


class PushOutBee(PPOutBee, TriggerTarget):
    mode = "push"


class PullOutBee(PPOutBee):
    mode = "pull"


def push_out(target):
    # TODO: nice error message
    is_valid_bee = isinstance(target, Stateful) or isinstance(target, Output) or target.implements(Callable)

    if get_mode() == "immediate":
        assert is_valid_bee or callable(target)
        return PushOut(target)

    else:
        assert is_valid_bee, target
        return PushOutBee(target)


def pull_out(target):
    # TODO: nice error message
    is_valid_bee = isinstance(target, Stateful) or isinstance(target, Output) or target.implements(Callable)

    if get_mode() == "immediate":
        assert is_valid_bee or callable(target), target
        return PullOut(target)

    else:
        assert is_valid_bee, target
        return PullOutBee(target)
