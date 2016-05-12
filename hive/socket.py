from .manager import memoize, get_building_hive, ContextFactory
from .mixins import ConnectTarget, Plugin, Socket, Callable, Exportable, Bee, Bindable, Nameable
from .policies import SingleRequired


class HiveSocket(Socket, ConnectTarget, Bindable, Exportable, Nameable):

    def __init__(self, func, data_type=None, run_hive=None):
        assert callable(func) or isinstance(func, Callable), func
        self._run_hive = run_hive
        self._func = func

        self.data_type = data_type

    def __repr__(self):
        return "<Socket: {}>".format(self._func)

    @memoize
    def bind(self, run_hive):
        if self._run_hive:
            return self

        if isinstance(self._func, Bindable):
            func = self._func.bind(run_hive)

        else:
            func = self._func

        return self.__class__(func, self.data_type, run_hive)

    @memoize
    def export(self):
        # TODO: somehow log the redirection path
        func = self._func

        if isinstance(func, Exportable):
            exported = func.export()
            return self.__class__(exported, self.data_type, self._run_hive)

        else:
            return self
    
    def _hive_is_connectable_target(self, source):
        if not isinstance(source, Plugin):
            raise ValueError("Socket source must be a subclass of Plugin")

    def _hive_connect_target(self, source):
        plugin = source.plugin()
        self._func(plugin)
    

class HiveSocketBee(Socket, ConnectTarget, Exportable):

    def __init__(self, target, identifier=None, data_type=None, policy=None, export_to_parent=False):
        self._hive_object_cls = get_building_hive()
        self._target = target

        self.identifier = identifier
        self.data_type = data_type
        self.export_to_parent = export_to_parent

        if policy is None:
            policy = SingleRequired

        self.policy = policy

    def __repr__(self):
        return "<Socket: {}>".format(self._target)

    @memoize
    def getinstance(self, hive_object):
        target = self._target
        if isinstance(target, Bee):
            target = target.getinstance(hive_object)

        return HiveSocket(target, self.data_type)

    @memoize
    def export(self):
        # TODO: somehow log the redirection path
        target = self._target
        if isinstance(target, Exportable):
            exported = target.export()

            return self.__class__(exported, self.identifier, self.data_type, self.policy, self.export_to_parent)

        else:
            return self


socket = ContextFactory("hive.socket", immediate_mode_cls=HiveSocket, build_mode_cls=HiveSocketBee)