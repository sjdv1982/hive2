import hive

from ..bind import BindInfo


class EntityEnvironmentClass:

    def __init__(self, context, bind_id):
        self._identifier = bind_id
        self._entity = None

        self._hive = hive.get_run_hive()
        plugins = context.plugins['entity']

        self._get_entity = plugins['get_entity']
        self._get_position_absolute = plugins['get_position_absolute']
        self._get_position_relative = plugins['get_position_relative']
        self._get_orientation_absolute = plugins['get_orientation_absolute']
        self._get_orientation_relative = plugins['get_orientation_relative']

        self._entity = self._get_entity(bind_id)

    def get_bound_object(self):
        return self._entity

    def get_entity(self, identifier):
        return self._get_entity(identifier)

    def get_position_absolute(self, entity):
        return self._get_position_absolute(entity)

    def get_orientation_absolute(self, entity):
        return self._get_orientation_absolute(entity)

    def get_position_relative(self, entity, other):
        return self._get_position_relative(entity, other)

    def get_orientation_relative(self, entity, other):
        return self._get_orientation_relative(entity, other)


def declare_entity_environment(meta_args):
    pass


def build_entity_environment(cls, i, ex, args, meta_args):
    """Runtime event environment for instantiated hive.

    Provides appropriate sockets and plugins for event interface
    """
    ex.get_bound_entity = hive.plugin(cls.get_bound_entity)

    ex.get_entity = hive.plugin(cls.get_entity, identifier=("entity", "get"))
    ex.get_position_absolute = hive.plugin(cls.get_position_absolute, identifier=("entity", "position", "absolute",
                                                                                  "get"))
    ex.get_position_relative = hive.plugin(cls.get_position_relative, identifier=("entity", "position", "relative",
                                                                                  "get"))
    ex.get_orientation_absolute = hive.plugin(cls.get_orientation_absolute, identifier=("entity", "orientation",
                                                                                        "absolute", "get"))
    ex.get_orientation_relative = hive.plugin(cls.get_orientation_relative, identifier=("entity", "orientation",
                                                                                        "relative", "get"))


EntityEnvironment = hive.meta_hive("EntityEnvironment", build_entity_environment, declare_entity_environment,
                                   cls=EntityEnvironmentClass)


class EntityCls:

    def __init__(self):
        self._hive = hive.get_run_hive()

        self._plugins = {}

    def set_get_entity(self, get_entity):
        self._plugins['get_entity'] = get_entity

    def set_get_position_absolute(self, plugin):
        self._plugins['get_position_absolute'] = plugin

    def set_get_position_relative(self, plugin):
        self._plugins['get_position_relative'] = plugin

    def set_get_orientation_absolute(self, plugin):
        self._plugins['get_orientation_absolute'] = plugin

    def entity_get_orientation_relative(self, plugin):
        self._plugins['get_orientation_relative'] = plugin

    def get_plugins(self):
        return {'entity': self._plugins}


def declare_bind(meta_args):
    meta_args.bind_entity = hive.parameter("bool", True)


def build_bind(cls, i, ex, args, meta_args):
    if not meta_args.bind_event:
        return

    ex.entity_get_get_entity = hive.socket(cls.set_get_entity, identifier=("entity", "get"))
    ex.entity_get_position_absolute = hive.plugin(cls.set_get_position_absolute,
                                                  identifier=("entity", "position", "absolute", "get"))
    ex.entity_get_position_relative = hive.plugin(cls.set_get_position_relative,
                                                  identifier=("entity", "position", "relative", "get"))
    ex.entity_get_orientation_absolute = hive.plugin(cls.set_get_orientation_absolute,
                                                     identifier=("entity", "orientation", "absolute", "get"))
    ex.entity_get_orientation_relative = hive.plugin(cls.set_get_orientation_relative,
                                                     identifier=("entity", "orientation", "relative", "get"))

    ex.entity_get_plugins = hive.plugin(cls.get_plugins, identifier=("bind", "get_plugins"))


BindEntity = hive.dyna_hive("BindEntity", build_bind, declarator=declare_bind, cls=EntityCls)


def is_enabled(meta_args):
    return meta_args.bind_entity


bind_info = BindInfo("entity", is_enabled, BindEntity, EntityEnvironment)
