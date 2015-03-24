"""
Hives that are TriggerSources can be used as the source argument in the trigger and pre_trigger commands
A TriggerSource must have _hive_trigger_source and _hive_pretrigger_source methods, invoked upon connection to the target
This method must return a callable or raise an informative HiveConnectError 
"""

from . import Connectable


class TriggerSource(Connectable):

    def _hive_trigger_source(self, targetfunc):
        raise NotImplementedError

    def _hive_pretrigger_source(self, targetfunc):
        raise NotImplementedError
