# Report2 - Unlike report.py, this module is designed to provide simple debugging information about hive current state
# This information is not intended to be efficiently packed (for non-localhost communication) or used to invoke IO
from json import loads, dumps

stack = []


def connect(source, target):
    class Connecter:

        def _hive_trigger_target(self):
            print("TRIG TARGET")

        def _hive_trigger_source(self):
            print("TRIG SOURCE")

        def _hive_


def push(source, target, data_type, value):
    stack.append(('push', source, target, data_type, value))


def pull(source, target, data_type, value):
    stack.append(('push', source, target, data_type, value))


def trigger(source, target, pretrigger):
    stack.append(('trigger', source, target, pretrigger))


def dump():
    return dumps(stack)


def load(data):
    return loads(data)