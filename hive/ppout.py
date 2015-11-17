from .mixins import Antenna, Output, Stateful, Bee, Bindable, Exportable, Callable, ConnectSource, ConnectTarget, \
    TriggerSource, TriggerTarget, Socket, Plugin
from .classes import HiveBee, Pusher
from .manager import get_mode, get_building_hive, memoize
from .tuple_type import types_match


import debug


class PPOutBase(Output, ConnectSource, TriggerSource, Bindable):
    def __init__(self, target, data_type, bound=None, run_hive=None):
        is_stateful = isinstance(target, Stateful)
        assert is_stateful or callable(target) or target.implements(Callable), target

        self._is_stateful = is_stateful
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
        if self._is_stateful:
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

    def push(self):
        # TODO: exception handling hooks
        self._pretrigger.push()

        if self._is_stateful:
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

    def _hive_connect_target(self, target):
        # If we use debugging
        if debug.enabled:
            report = debug.report.report_pull
            source_name = None
            target_name = None
            data_type = self.data_type

            def callback(value):
                nonlocal source_name, target_name
                if source_name is None:
                    source_name = ".".join(self._hive_bee_name)
                    target_name = ".".join(target._hive_bee_name)

                report(source_name, target_name, data_type, value)
                target.plugin(value)

        else:
            callback = target.plugin

        self._targets.append(callback)
            
    def _hive_trigger_target(self):
        return self.push

    __call__ = push


class PPOutBee(Output, ConnectSource, TriggerSource):
    mode = None

    def __init__(self, target):
        is_stateful_or_output = isinstance(target, (Stateful, Output))
        assert is_stateful_or_output or target.implements(Callable) # TODO: nice error message

        if is_stateful_or_output:
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
    if get_mode() == "immediate":
        return PushOut(target)

    else:
        return PushOutBee(target)


def pull_out(target):
    if get_mode() == "immediate":
        return PullOut(target)

    else:
        return PullOutBee(target)
