from .mixins import ConnectSource, ConnectTarget, Bee, Bindable
from .classes import HiveBee
from . import get_mode
from . import manager
from .hive import HiveObject


def build_connection(source, target):
    # TODO: register connection, or insert a listener function in between
    
    #will raise an Exception if incompatible:
    source._hive_connectable_source(target)
    target._hive_connectable_target(source)
        
    target._hive_connect_target(source)
    source._hive_connect_source(target)


class Connection(Bindable):

    def __init__(self, source, target):
        self.source = source
        self.target = target

    @manager.bind
    def bind(self, runhive):
        source = self.source
        if isinstance(source, Bindable):
            source = source.bind(runhive)

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(runhive)

        return build_connection(source, target)    


class ConnectionBee(HiveBee):

    def __init__(self, source, target):
        HiveBee.__init__(self, None, source, target)

    @manager.getinstance
    def getinstance(self, hiveobject):
        source, target = self.args
        if isinstance(source, HiveObject):
            #source = source.get_trigger_source()
            raise NotImplementedError

        if isinstance(source, Bee):
            source = source.getinstance(hiveobject)

        if isinstance(target, HiveObject):
            #target = target.get_trigger_target()            
            raise NotImplementedError

        if isinstance(target, Bee):    
            target = target.getinstance(hiveobject)

        if get_mode() == "immediate":            
            return build_connection(source, target)

        else:
            return Connection(source, target)


def connect(source, target):

    if isinstance(source, Bee):
        assert source.implements(ConnectSource), source
        assert target.implements(ConnectTarget), target

    else:
        assert isinstance(source, ConnectSource), source
        assert isinstance(target, ConnectTarget), target

    if get_mode() == "immediate":
        build_connection(source, target)

    else:
        connectionbee = ConnectionBee(source, target)        
        manager.register_bee(connectionbee)
        return connectionbee

