"""
Hives that are ConnectSourceBases can be used as the source argument in the connect command
They exist in two flavors:
- ConnectSource must have a _hive_connectable_source method, accepting a target ConnectTarget.
    The method must raise an informative HiveConnectError if the target is not connectable, nothing otherwise
    It must also have a _hive_connect_source method, invoked upon connection to the target
- ConnectSourceDerived must contain a _hive_connect_sources attribute
    This attribute must be a dict with string keys and ConnectSource values
"""

from . import Connectable


class ConnectSourceBase(Connectable):
    pass


class ConnectSource(ConnectSourceBase):

    def _hive_connectable_source(self, target):
        raise NotImplementedError

    def _hive_connect_source(self, target):
        raise NotImplementedError


class ConnectSourceDerived(ConnectSourceBase):    
    _hive_connect_sources = None
