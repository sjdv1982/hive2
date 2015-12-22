import hive

from ..bind import BindInfo


class SceneEnvironmentClass:

    def __init__(self, context, bind_id):
        self._identifier = bind_id
        self._leader = bind_id,
        self._handlers = []

        self._hive = hive.get_run_hive()

    def get_bound_object(self):
        return self._object


def declare_scene_environment(meta_args):
    pass


def build_scene_environment(cls, i, ex, args, meta_args):
    """Runtime event environment for instantiated hive.

    Provides appropriate sockets and plugins for event interface
    """
    ex.get_bound_object = hive.plugin(cls.get_bound_object)


SceneEnvironment = hive.meta_hive("SceneEnvironment", build_scene_environment, declare_scene_environment,
                                  cls=SceneEnvironmentClass)


class SceneCls:

    def __init__(self):
        self._hive = hive.get_run_hive()

        self._add_handler = None
        self._remove_handler = None

    def set_add_handler(self, add_handler):
        self._add_handler = add_handler

    def set_remove_handler(self, remove_handler):
        self._remove_handler = remove_handler

    def get_plugins(self):
        return {'event': {'add_handler': self._add_handler, 'remove_handler': self._remove_handler}}

    def get_config(self):
        dispatch_mode = self._hive._hive_object._hive_meta_args_frozen.event_dispatch_mode
        return {'event': {'dispatch_mode': dispatch_mode}}


def declare_bind(meta_args):
    meta_args.bind_event = hive.parameter("bool", True)
    meta_args.event_dispatch_mode = hive.parameter("str", 'by_leader', {'by_leader', 'all'})


def build_bind(cls, i, ex, args, meta_args):
    if not meta_args.bind_event:
        return

    ex.event_set_add_handler = hive.socket(cls.set_add_handler, identifier=("event", "add_handler"))
    ex.event_set_remove_handler = hive.socket(cls.set_remove_handler, identifier=("event", "remove_handler"))
    ex.event_get_plugins = hive.plugin(cls.get_plugins, identifier=("bind", "get_plugins"))
    ex.event_get_config = hive.plugin(cls.get_config, identifier=("bind", "get_config"))


BindScene = hive.dyna_hive("BindScene", build_bind, declarator=declare_bind, cls=SceneCls)


def is_enabled(meta_args):
    return meta_args.bind_scene


bind_info = BindInfo("scene", is_enabled, BindScene, SceneEnvironment)
