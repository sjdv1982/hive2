import hive

from ..bind import BindInfo


class EntityEnvironmentClass:

    def __init__(self, context):
        self._hive = hive.get_run_hive()

        plugins = context.plugins['entity']
        config = context.config['entity']

        self._get_entity = plugins['get_entity']

        self._get_position_absolute = plugins['get_position_absolute']
        self._get_position_relative = plugins['get_position_relative']

        self._set_position_absolute = plugins['set_position_absolute']
        self._set_position_relative = plugins['set_position_relative']

        self._get_orientation_absolute = plugins['get_orientation_absolute']
        self._get_orientation_relative = plugins['get_orientation_relative']

        self._set_orientation_absolute = plugins['set_orientation_absolute']
        self._set_orientation_relative = plugins['set_orientation_relative']

        self._get_parent = plugins['get_parent']
        self._set_parent = plugins['set_parent']

        self._get_tag = plugins['get_tag']
        self._set_tag = plugins['set_tag']

        self._register_destructor = plugins['register_destructor']
        self._destroy_entity = plugins['destroy_entity']
        self._spawn_entity = plugins['spawn_entity']

        self._entity = config['entity']

        # Add reference to this hive for this entity
        if self._entity is not None:
            self._register_destructor(self._entity, self.destroy)

    def destroy(self):
        self._hive.on_stopped()

    def get_bound_entity(self):
        return self._entity

    def get_entity(self, identifier):
        return self._get_entity(identifier)

    def destroy_entity(self, entity):
        self._destroy_entity(entity)

    def spawn_entity(self, template_name):
        return self._spawn_entity(template_name)

    def get_position_absolute(self, entity):
        return self._get_position_absolute(entity)

    def get_position_relative(self, entity, other):
        return self._get_position_relative(entity, other)

    def set_position_absolute(self, entity, position):
        self._set_position_absolute(entity, position)

    def set_position_relative(self, entity, other, position):
        self._set_position_relative(entity, other, position)

    def get_orientation_absolute(self, entity):
        return self._get_orientation_absolute(entity)

    def get_orientation_relative(self, entity, other):
        return self._get_orientation_relative(entity, other)

    def set_orientation_absolute(self, entity, orientation):
        self._set_orientation_absolute(entity, orientation)

    def set_orientation_relative(self, entity, other, orientation):
        self._set_orientation_relative(entity, other, orientation)

    def register_destructor(self, entity, destructor):
        self._register_destructor(entity, destructor)

    def set_parent(self, entity, parent):
        self._set_parent(entity, parent)

    def get_parent(self, entity):
        return self._get_parent(entity)

    def set_tag(self, entity, tag, value):
        self._set_tag(entity, tag, value)

    def get_tag(self, entity, tag):
        return self._get_tag(entity, tag)


def declare_entity_environment(meta_args):
    pass


def build_entity_environment(cls, i, ex, args, meta_args):
    """Runtime event environment for instantiated hive.

    Provides appropriate sockets and plugins for event interface
    """
    if meta_args.bind_meta_args.bind_entity == "bound":
        ex.get_bound_entity = hive.plugin(cls.get_bound_entity, identifier="entity.get_bound")

    ex.get_entity = hive.plugin(cls.get_entity, identifier="entity.get")

    ex.get_position_absolute = hive.plugin(cls.get_position_absolute, identifier="entity.position.get.absolute")
    ex.get_position_relative = hive.plugin(cls.get_position_relative, identifier="entity.position.get.relative")
    ex.set_position_absolute = hive.plugin(cls.set_position_absolute, identifier="entity.position.set.absolute")
    ex.set_position_relative = hive.plugin(cls.set_position_relative, identifier="entity.position.set.relative")

    ex.get_orientation_absolute = hive.plugin(cls.get_orientation_absolute, identifier="entity.orientation.get.absolute")
    ex.get_orientation_relative = hive.plugin(cls.get_orientation_relative, identifier="entity.orientation.get.relative")
    ex.set_orientation_absolute = hive.plugin(cls.set_orientation_absolute, identifier="entity.orientation.set.absolute")
    ex.set_orientation_relative = hive.plugin(cls.set_orientation_relative, identifier="entity.orientation.set.relative")

    ex.get_parent = hive.plugin(cls.get_parent, identifier="entity.parent.get")
    ex.set_parent = hive.plugin(cls.set_parent, identifier="entity.parent.set")

    ex.get_tag = hive.plugin(cls.get_tag, identifier="entity.tag.get")
    ex.set_tag = hive.plugin(cls.set_tag, identifier="entity.tag.set")

    ex.destroy_entity = hive.plugin(cls.destroy_entity, identifier="entity.destroy")
    ex.spawn_entity = hive.plugin(cls.spawn_entity, identifier="entity.spawn")

    ex.register_destructor = hive.plugin(cls.register_destructor, identifier="entity.register_destructor")


EntityEnvironment = hive.meta_hive("EntityEnvironment", build_entity_environment, declare_entity_environment,
                                   cls=EntityEnvironmentClass)


class EntityCls:

    def __init__(self):
        self._hive = hive.get_run_hive()
        self._plugins = {}

        self.entity = None

    def set_get_entity(self, get_entity):
        self._plugins['get_entity'] = get_entity

    def set_get_position_absolute(self, plugin):
        self._plugins['get_position_absolute'] = plugin

    def set_get_position_relative(self, plugin):
        self._plugins['get_position_relative'] = plugin

    def set_set_position_absolute(self, plugin):
        self._plugins['set_position_absolute'] = plugin

    def set_set_position_relative(self, plugin):
        self._plugins['set_position_relative'] = plugin

    def set_get_orientation_absolute(self, plugin):
        self._plugins['get_orientation_absolute'] = plugin

    def set_get_orientation_relative(self, plugin):
        self._plugins['get_orientation_relative'] = plugin

    def set_set_orientation_absolute(self, plugin):
        self._plugins['set_orientation_absolute'] = plugin

    def set_set_orientation_relative(self, plugin):
        self._plugins['set_orientation_relative'] = plugin

    def set_get_parent(self, plugin):
        self._plugins['get_parent'] = plugin

    def set_set_parent(self, plugin):
        self._plugins['set_parent'] = plugin

    def set_get_tag(self, plugin):
        self._plugins['get_tag'] = plugin

    def set_set_tag(self, plugin):
        self._plugins['set_tag'] = plugin

    def set_destroy_entity(self, destroy_entity):
        self._plugins['destroy_entity'] = destroy_entity

    def set_spawn_entity(self, spawn_entity):
        self._plugins['spawn_entity'] = spawn_entity

    def set_register_hive_destructor(self, register_destructor):
        self._plugins['register_destructor'] = register_destructor

    def get_plugins(self):
        return {'entity': self._plugins}

    def get_config(self):
        this_config = {}
        config = {'entity': this_config}

        bound_to_entity = self._hive._hive_object._hive_meta_args_frozen.bind_entity == 'bound'

        if bound_to_entity:
            self._hive.entity()
            this_config['entity'] = self.entity

        else:
            this_config['entity'] = None

        return config


def declare_bind(meta_args):
    meta_args.bind_entity = hive.parameter("str", 'bound', {'none', 'bound', 'unbound'})


def build_bind(cls, i, ex, args, meta_args):
    bind_mode = meta_args.bind_entity

    if bind_mode == 'none':
        return

    ex.entity_get_entity = hive.socket(cls.set_get_entity, identifier="entity.get")

    ex.entity_get_position_absolute = hive.socket(cls.set_get_position_absolute,
                                                  identifier="entity.position.get.absolute")
    ex.entity_get_position_relative = hive.socket(cls.set_get_position_relative,
                                                  identifier="entity.position.get.relative")

    ex.entity_set_position_absolute = hive.socket(cls.set_set_position_absolute,
                                                  identifier="entity.position.set.absolute")
    ex.entity_set_position_relative = hive.socket(cls.set_set_position_relative,
                                                  identifier="entity.position.set.relative")

    ex.entity_get_orientation_absolute = hive.socket(cls.set_get_orientation_absolute,
                                                     identifier="entity.orientation.get.absolute")
    ex.entity_get_orientation_relative = hive.socket(cls.set_get_orientation_relative,
                                                     identifier="entity.orientation.get.relative")

    ex.entity_set_orientation_absolute = hive.socket(cls.set_set_orientation_absolute,
                                                     identifier="entity.orientation.set.absolute")
    ex.entity_set_orientation_relative = hive.socket(cls.set_set_orientation_relative,
                                                     identifier="entity.orientation.set.relative")

    ex.entity_get_parent = hive.socket(cls.set_get_parent, identifier="entity.parent.get")
    ex.entity_set_parent = hive.socket(cls.set_set_parent, identifier="entity.parent.set")

    ex.entity_get_tag = hive.socket(cls.set_get_tag, identifier="entity.tag.get")
    ex.entity_set_tag = hive.socket(cls.set_set_tag, identifier="entity.tag.set")

    ex.entity_get_register_hive_destructor = hive.socket(cls.set_register_hive_destructor,
                                                         identifier="entity.register_destructor")
    ex.entity_destroy = hive.socket(cls.set_destroy_entity, identifier="entity.destroy")
    ex.entity_spawn = hive.socket(cls.set_spawn_entity, identifier="entity.spawn")

    if bind_mode == 'bound':
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)

    ex.entity_get_plugins = hive.plugin(cls.get_plugins, identifier="bind.get_plugins")
    ex.entity_get_config = hive.plugin(cls.get_config, identifier="bind.get_config")


BindEntity = hive.dyna_hive("BindEntity", build_bind, declarator=declare_bind, cls=EntityCls)


def get_environments(meta_args):
    if meta_args.bind_entity != 'none':
        return EntityEnvironment,

    return ()


bind_info = BindInfo("entity", BindEntity, get_environments)
