from collections import namedtuple

BoundRuntimeInfo = namedtuple("BoundRuntimeInfo", "parent name")


class Bee(object):
    _hive_object_cls = None
    _hive_wrapper_name = None

    def implements(self, cls):
        return isinstance(self, cls)

    def getinstance(self, hive_object):
        return self


class Parameter(object):
    _hive_parameter_name = None

    start_value = None
    data_type = None
    options = None

    class NoValue(object):
        pass


class Connectable(object):
    # Connectables don't need to be Bees!
    pass


class Bindable(object):
    # Connectables don't need to be Bees!
    pass


class Nameable(object):

    _hive_runtime_info = None

    def add_runtime_info(self, parent, name):
        info = BoundRuntimeInfo(parent, name)

        if self._hive_runtime_info is None:
            self._hive_runtime_info = set()

        self._hive_runtime_info.add(info)


class Callable(Bee):
    pass


class Exportable(Bee):
    export_only = True

    def export(self):
        raise NotImplementedError


class Plugin(Bee):
    pass


class Socket(Bee):
    pass


class IO(Bee):
    pass


class Antenna(IO):
    mode = None #must be push or pull

    def push(self): #only needs to be defined if mode is "push"
        raise NotImplementedError 


class Output(IO):
    mode = None #must be push or pull

    def pull(self): #only needs to be defined if mode is "pull"
        raise NotImplementedError


from .connect_source import ConnectSourceBase, ConnectSource, ConnectSourceDerived
from .connect_target import ConnectTargetBase, ConnectTarget, ConnectTargetDerived
from .stateful import Stateful
from .trigger_source import TriggerSourceBase, TriggerSource, TriggerSourceDerived
from .trigger_target import TriggerTargetBase, TriggerTarget, TriggerTargetDerived

