from .mixins import ConnectSourceBase, ConnectSourceDerived, ConnectTargetBase, ConnectTargetDerived, Bee, Bindable, \
    Exportable
from .classes import HiveBee
from .manager import get_mode, memoize, register_bee
from .tuple_type import types_match

from itertools import product


def find_connection_candidates(sources, targets, require_types=True):
    """Finds appropriate connections between ConnectionSources and ConnectionTargets

    :param sources: connection sources
    :param targets: connection targets
    :param require_types: require type definitions to be declared
    """
    candidates = []

    for source_candidate, target_candidate in product(sources, targets):
        source_data_type = source_candidate.data_type
        target_data_type = target_candidate.data_type

        if require_types and not (source_data_type and target_data_type):
            continue

        if not types_match(source_data_type, target_data_type):
            continue

        candidates.append((source_candidate, target_candidate))

    return candidates


def connect_hives(source, target):
    if not source._hive_can_connect_hive(target):
        raise ValueError("Both hives must be either Hive runtimes or Hive objects")

    # Find source hive ConnectSources
    connect_sources = source._hive_find_connect_sources()

    # Find target hive ConnectSources
    connect_targets = target._hive_find_connect_targets()

    # First try: match candidates with named data_type
    candidates = find_connection_candidates(connect_sources, connect_targets)

    if not candidates:
        candidates = find_connection_candidates(connect_sources, connect_targets, require_types=False)

    if not candidates:
        raise ValueError("No matching connections found")

    elif len(candidates) > 1:
        candidate_names = [(a.attrib, b.attrib) for a, b in candidates]
        raise TypeError("Multiple matches found between {} and {}: {}".format(source, target, candidate_names))

    source_candidate, target_candidate = candidates[0]

    source_bee = getattr(source, source_candidate.attrib)
    target_bee = getattr(target, target_candidate.attrib)

    return source_bee, target_bee


def build_connection(source, target):
    # TODO: register connection, or insert a listener function in between
    hive_source = isinstance(source, ConnectSourceDerived)
    hive_target = isinstance(target, ConnectTargetDerived)

    # Find appropriate bees to connect within respective hives
    if hive_source and hive_target:
        source, target = connect_hives(source, target)

    else: 
        if hive_source:
            source = source._hive_get_connect_source(target)

        elif hive_target:
            target = target._hive_get_connect_target(source)


    # will raise an Exception if incompatible:
    source._hive_is_connectable_source(target)
    target._hive_is_connectable_target(source)

    if False:
        target._hive_connect_target(source)
        source._hive_connect_source(target)
    else:
        from debug import report2
        dsource, dtarget = report2.connect(source, target)
        target._hive_connect_target(dtarget)
        source._hive_connect_target(dsource)


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

