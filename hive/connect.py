from .mixins import ConnectSourceBase, ConnectSourceDerived, ConnectTargetBase, ConnectTargetDerived, Bee, Bindable, \
    Exportable
from .classes import HiveBee
from .manager import get_mode, memoize, register_bee
from .hive import connect_hives


def connect_hive_hive(source, target):
    raise NotImplementedError


def build_connection(source, target):
    # TODO: register connection, or insert a listener function in between
    hive_source = isinstance(source, ConnectSourceDerived)
    hive_target = isinstance(target, ConnectTargetDerived)

    # Find appropriate bees to connect within respective hives
    if hive_source and hive_target:
        source, target = connect_hives(source, target)

    else: 
        if hive_source:
            source = source._hive_find_connect_source(target)

        elif hive_target:
            target = target._hive_find_connect_target(source)
                    
    # will raise an Exception if incompatible:
    source._hive_is_connectable_source(target)
    target._hive_is_connectable_target(source)
        
    target._hive_connect_target(source)
    source._hive_connect_source(target)


class Connection(Bindable):

    def __init__(self, source, target):
        self.source = source
        self.target = target

    def __repr__(self):
        return "<Connection {} ~> {}>".format(self.source.repr(), self.target)

    @memoize
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

    def __repr__(self):
        return "<ConnectionBee\n\t{}\n\t{}>".format(*self.args)

    @memoize
    def getinstance(self, hive_object):
        source, target = self.args

        if isinstance(source, Bee):
            if isinstance(source, Exportable):
                source = source.export()

            source = source.getinstance(hive_object)

        if isinstance(target, Bee):
            if isinstance(target, Exportable):
                target = target.export()

            target = target.getinstance(hive_object)

        if get_mode() == "immediate":            
            return build_connection(source, target)

        else:
            return Connection(source, target)


def connect(source, target):

    if isinstance(source, Bee):
        assert source.implements(ConnectSourceBase), source
        assert isinstance(target, Bee), target
        assert target.implements(ConnectTargetBase), target

    else:
        assert isinstance(source, ConnectSourceBase), source
        assert isinstance(target, ConnectTargetBase), target

    if get_mode() == "immediate":
        build_connection(source, target)

    else:
        connection_bee = ConnectionBee(source, target)
        register_bee(connection_bee)
        return connection_bee

