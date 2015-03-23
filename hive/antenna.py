"""
from .mixins import Antenna, Output, Stateful, ConnectTarget, TriggerSource, TriggerTarget, Bee, Bindable, Exportable, Callable
from .classes import HiveBee, Pusher
from . import get_mode
from . import manager


def compare_types(b1, b2):
        for t1, t2 in zip(b1.datatype, b2.datatype):
                if t1 != t2:
                        raise TypeError((b1.datatype, b2.datatype)) # TODO: nice error message

class AntennaBase(Antenna, ConnectTarget, TriggerSource, Bindable):
        def __init__(self, target, datatype, bound=False, runhive=None):
                assert isinstance(target, Stateful) or target.implements(Callable), target
                self._stateful = isinstance(target, Stateful)
                self.target = target
                self.datatype = datatype
                self._bound = bound
                self._runhive = runhive
                self._trig = Pusher(self)
                self._pretrig = Pusher(self)                
                                
        def _hive_trigger_source(self, targetfunc):
                self._trig.add_target(targetfunc)
        def _hive_pretrigger_source(self, targetfunc):
                self._pretrig.add_target(targetfunc)
                                
        @manager.bind
        def bind(self, runhive):
                self._runhive = runhive
                if self._bound: return self
                target = self.target
                if isinstance(target, Bindable):
                        target = target.bind(runhive)
                ret = self.__class__(target, self.datatype, bound=True, runhive=runhive)
                return ret                

class PushAntenna(AntennaBase):
        mode = "push"
        def push(self, value):
                # TODO: exception handling hooks
                self._pretrig.push()
                if self._stateful:
                        self.target._hive_stateful_setter(self._runhive, value)
                else:
                        self.target(value)
                self._trig.push()
        def _hive_connectable_target(self, source):
                assert isinstance(source, Output) # TODO : nicer error message
                assert source.mode == "push" # TODO : nicer error message
                compare_types(source, self)
        def _hive_connect_target(self, source):
                pass                
                        

class PullAntenna(AntennaBase, TriggerTarget):
        mode = "pull"
        _pull_callback = None
        def pull(self):
                # TODO: exception handling hooks
                self._pretrig.push()
                value = self._pull_callback()
                if self._stateful:
                        self.target._hive_stateful_setter(self._runhive, value)
                else:
                        self.target(value)                        
                self._trig.push()                
        def _hive_connectable_target(self, source):
                assert isinstance(source, Output) # TODO : nicer error message
                assert source.mode == "pull" # TODO : nicer error message
                compare_types(source, self)
        def _hive_connect_target(self, source):
                if self._pull_callback is not None:
                        raise TypeError("PullAntenna cannot accept more than one connection") # TODO: nicer error message, with names
                self._pull_callback = source.pull
        
        def _hive_trigger_target(self):
                return self.pull

class AntennaBee(HiveBee, Antenna, ConnectTarget, TriggerSource, Exportable):
        def __init__(self, mode, target, *datatype):
                assert mode in ("push", "pull")
                self.mode = mode
                self.datatype = datatype # TODO: retrieve datatype info from target and check that it matches (TODO add it to h.property and h.buffer)
                assert isinstance(target, Stateful) or isinstance(target, Antenna) or target.implements(Callable) # TODO: nice error message
                HiveBee.__init__(self, None, target)
        @manager.getinstance
        def getinstance(self, hiveobject):                
                target, = self.args
                if isinstance(target, Bee): 
                        target = target.getinstance(hiveobject)                        
                if self.mode == "push":        
                        ret = PushAntenna(target, self.datatype)        
                else:
                        ret = PullAntenna(target, self.datatype)        
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
                if cls == TriggerTarget and self.mode == "pull":
                        return True
                return False
                
def antenna(mode, target, *datatype):
        assert mode in ("push", "pull"), mode # TODO: nicer error message
        assert isinstance(target, Bee), target # TODO: nicer error message
        if get_mode() == "immediate":
                if isinstance(target, Exportable):
                        target = target.export()                
                assert isinstance(target, Stateful) or target.implements(Callable) # TODO: nicer error message
                if mode == "push":
                        return PushAntenna(target, *datatype)                
                else:
                        return PullAntenna(target, *datatype)                
        else:
                return AntennaBee(mode, target, *datatype)
"""

from .mixins import Antenna, Exportable
from . import get_building_hive
from .context_factory import ContextFactory


class HiveAntenna(Antenna, Exportable):

    def __init__(self, target):
        assert isinstance(target, Antenna), target
        self._hive_cls = get_building_hive()
        self._target = target

    def export(self):
        # TODO: somehow log the redirection path
        target = self._target

        if isinstance(target, Exportable):
            target = target.export()

        return target


antenna = ContextFactory("hive.antenna", deferred_cls=HiveAntenna)
