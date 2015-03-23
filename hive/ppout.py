from .mixins import Antenna, Output, Stateful, Bee, Bindable, Exportable, Callable
from .mixins import ConnectSource, ConnectTarget, TriggerSource, TriggerTarget, Socket, Plugin
from .classes import HiveBee, Pusher
from . import get_mode, get_building_hive
from . import manager
from .ppin import compare_types


class PPOutBase(Output, ConnectSource, TriggerSource, Bindable):

    def __init__(self, target, datatype, bound=False, runhive=None):
        assert isinstance(target, Stateful) or target.implements(Callable), target
        self._stateful = isinstance(target, Stateful)
        self.target = target
        self.datatype = datatype
        self._bound = bound
        self._runhive = runhive
        self._trig = Pusher(self)
        self._pretrig = Pusher(self)                
                
    @manager.bind
    def bind(self, runhive):
        self._runhive = runhive
        if self._bound:
            return self

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(runhive)

        ret = self.__class__(target, self.datatype, bound=True, runhive=runhive)
        return ret        

    def _hive_trigger_source(self, targetfunc):
        self._trig.add_target(targetfunc)

    def _hive_pretrigger_source(self, targetfunc):
        self._pretrig.add_target(targetfunc)


class PullOut(PPOutBase):
    mode = "pull"

    def pull(self):
        #TODO: exception handling hooks
        self._pretrig.push()
        if self._stateful:
            value = self.target._hive_stateful_getter(self._runhive)
        else:
            value = self.target()
        self._trig.push()
        return value

    def _hive_connectable_source(self, target):
        assert isinstance(target, Antenna) #TODO : nicer error message
        assert target.mode == "pull" #TODO : nicer error message
        compare_types(self, target)

    def _hive_connect_source(self, target):
        pass

    
class PushOut(PPOutBase, Socket, ConnectTarget, TriggerTarget):
    mode = "push"

    def __init__(self, target, datatype, bound=False, runhive=None):
        PPOutBase.__init__(self, target, datatype, bound, runhive)
        self._targets = []

    def __call__(self):
        self.push()

    def push(self):
        #TODO: exception handling hooks
        self._pretrig.push()

        if self._stateful:
            value = self.target._hive_stateful_getter(self._runhive)

        else:
            value = self.target()

        for target in self._targets:
            target(value)

        self._trig.push()

    def socket(self):
        return self.push
    
    def _hive_connectable_source(self, target):
        assert isinstance(target, Antenna), target #TODO : nicer error message
        assert target.mode == "push" #TODO : nicer error message    
        compare_types(target, self)
    
    def _hive_connect_source(self, target): #Socket
        self._targets.append(target.push)
            
    def _hive_connectable_target(self, source):
        assert isinstance(source, Plugin), source #TODO : nicer error message

    def _hive_connect_target(self, source):
        self._targets.append(source.plugin)
            
    def _hive_trigger_target(self):
        return self.push


class PPOutBee(Output, ConnectSource, TriggerSource):
    mode = None

    def __init__(self, target):        
        assert isinstance(target, Stateful) or isinstance(target, Output) or target.implements(Callable) #TODO: nice error message
        if isinstance(target, Stateful) or isinstance(target, Output):
            self.datatype = target.datatype

        else:
            self.datatype = ()

        self._hive_cls = get_building_hive()
        self.target = target

    @manager.getinstance
    def getinstance(self, hive_object):
        target = self.target

        if isinstance(target, Bee): 
            target = target.getinstance(hive_object)

        if self.mode == "push":    
            instance = PushOut(target, self.datatype)

        else:
            instance = PullOut(target, self.datatype)

        return instance

    def implements(self, cls):
        if isinstance(self, cls):
            return True

        target = self.target
        if isinstance(target, Bee):
            return target.implements(cls)

        return False


class PushOutBee(PPOutBee, TriggerTarget):
    mode = "push"


class PullOutBee(PPOutBee):
    mode = "pull"


def pushout(target):
    # TODO: nice error message
    assert isinstance(target, Stateful) or isinstance(target, Output) or target.implements(Callable)

    if get_mode() == "immediate":
        return PushOut(target)

    else:
        return PushOutBee(target)


def pullout(target):
    # TODO: nice error message
    assert isinstance(target, Stateful) or isinstance(target, Output) or target.implements(Callable)

    if get_mode() == "immediate":
        return PullOut(target)

    else:
        return PullOutBee(target)
