from .mixins import ConnectSource, ConnectSourceBase, ConnectSourceDerived, ConnectTarget, ConnectTargetBase, ConnectTargetDerived, Bee, Bindable
from .classes import HiveBee
from . import get_mode
from . import manager
from .hive import connect_hives


def build_connection(source, target):
    # TODO: register connection, or insert a listener function in between
    
    hive_source = isinstance(source, ConnectSourceDerived)
    hive_target = isinstance(target, ConnectTargetDerived)
    if hive_source and hive_target:
        source, target = connect_hives(source, target)
    else: 
        if hive_source:
            source = source._hive_search_connect_source(target)
        elif hive_target:
            target = target._hive_search_connect_target(source)
                    
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
    def bind(self, run_hive):
        source = self.source
        if isinstance(source, Bindable):
            source = source.bind(run_hive)

        target = self.target
        if isinstance(target, Bindable):
            target = target.bind(run_hive)

        return build_connection(source, target)    


class ConnectionBee(HiveBee):

    def __init__(self, source, target):
        HiveBee.__init__(self, None, source, target)

    @manager.getinstance
    def getinstance(self, hive_object):
        source, target = self.args
        if isinstance(source, Bee):
            source = source.getinstance(hive_object)

        if isinstance(target, Bee):    
            target = target.getinstance(hive_object)

        if get_mode() == "immediate":            
            return build_connection(source, target)

        else:
            return Connection(source, target)


def connect(source, target):

    if isinstance(source, Bee):
        assert source.implements(ConnectSourceBase), source
        assert target.implements(ConnectTargetBase), target

    else:
        assert isinstance(source, ConnectSourceBase), source
        assert isinstance(target, ConnectTargetBase), target

    if get_mode() == "immediate":
        build_connection(source, target)

    else:
        connectionbee = ConnectionBee(source, target)        
        manager.register_bee(connectionbee)
        return connectionbee

