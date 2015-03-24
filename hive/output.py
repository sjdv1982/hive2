"""
from .mixins import Antenna, Output, Stateful, Bee, Bindable, Exportable
from .mixins import ConnectSource, ConnectTarget, TriggerSource, TriggerTarget, Socket, Plugin
from .classes import HiveBee, Pusher
from . import get_mode
from . import manager
from .antenna import compare_types

class OutputBase(Output, ConnectSource, TriggerSource, Bindable):
    def __init__(self, target, data_type, bound=False, run_hive=None):
        assert isinstance(target, Stateful) or target.implements(Callable), target
        self._stateful = isinstance(target, Stateful)
        self.target = target
        self.data_type = data_type
        self._bound = bound
        self._run_hive = run_hive
        self._trigger = Pusher(self)
        self._pretrigger = Pusher(self)
                
    @manager.bind
    def bind(self, run_hive):
        self._run_hive = run_hive
        if self._bound: return self
        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(run_hive)
        ret = self.__class__(target, self.data_type, bound=True, run_hive=run_hive)
        return ret        

    def _hive_trigger_source(self, targetfunc):
        self._trigger.add_target(targetfunc)
    def _hive_pretrigger_source(self, targetfunc):
        self._pretrigger.add_target(targetfunc)

class PullOutput(OutputBase):
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
    def _hive_connectable_source(self, target):
        assert isinstance(target, Antenna) # TODO : nicer error message
        assert target.mode == "pull" # TODO : nicer error message
        compare_types(self, target)
    def _hive_connect_source(self, target):
        pass        
    
class PushOutput(OutputBase, Socket, ConnectTarget, TriggerTarget):
    mode = "push"
    def __init__(self, target, data_type, bound=False, run_hive=None):
        OutputBase.__init__(self, target, data_type, bound, run_hive)
        self._targets = []
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
    
    def _hive_connectable_source(self, target):
        assert isinstance(target, Antenna), target # TODO : nicer error message
        assert source.mode == "push" # TODO : nicer error message
        compare_types(target, self)
    def _hive_connect_source(self, target):
        self._targets.append(target.push)
            
    def _hive_connectable_target(self, source):
        assert isinstance(source, Plugin), source # TODO : nicer error message
    def _hive_connect_target(self, source):
        self._targets.append(source.plugin)
            
    def _hive_trigger_target(self):
        return self.push
    

class OutputBee(HiveBee, Output, ConnectSource, TriggerSource, Exportable):
    def __init__(self, mode, target, *data_type):
        assert mode in ("push", "pull")
        self.mode = mode
        self.data_type = data_type # TODO: retrieve data_type info from target and check that it matches (TODO add it to h.property and h.buffer)
        assert isinstance(target, Stateful) or isinstance(target,Output) or target.implements(Callable) # TODO: nice error message
        HiveBee.__init__(self, None, target)
    @manager.getinstance
    def getinstance(self, hiveobject):        
        target, = self.args
        if isinstance(target, Bee): 
            target = target.getinstance(hiveobject)            
        if self.mode == "push":    
            ret = PushOutput(target, self.data_type)
        else:
            ret = PullOutput(target, self.data_type)
        return ret
    def export(self):
        target, = self.args
        if isinstance(target, Stateful):
            return self
        elif isinstance(target, Exportable):
            return target.export()
        else:
            return target
    def implements(self, cls):
        if HiveBee.implements(self, cls):
            return True
        if cls == TriggerTarget and self.mode == "push":
            return True
        return False
        
def output(mode, target, *data_type):
    assert mode in ("push", "pull"), mode # TODO: nicer error message
    assert isinstance(target, Bee), target # TODO: nicer error message
    if get_mode() == "immediate":
        if isinstance(target, Exportable):
            target = target.export()        
        assert isinstance(target, Stateful) or target.implements(Callable) # TODO: nicer error message
        if mode == "push":
            return PushOutput(target, *data_type)
        else:
            return PullOutput(target, *data_type)
    else:
        return OutputBee(mode, target, *data_type)
"""
from .mixins import Output, Exportable
from .context_factory import ContextFactory
from . import get_building_hive


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