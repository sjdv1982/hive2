"""
Hives that are TriggerTargets can be used as the target argument in the trigger and pretrigger commands
A TriggerTarget must have a _hive_trigger_target method
This method must return a callable or raise an informative HiveConnectError 
"""

from . import Connectable


class TriggerTarget(Connectable):

    def _hive_trigger_target(self):
        raise NotImplementedError
