import hive

from ..bind import BindInfo, BindClassDefinition


definition = BindClassDefinition()
bind_mode = definition.parameter("bind_entity", "str", 'bound', {'none', 'bound', 'unbound'})

with definition.condition(bind_mode != "none"):
    definition.forward_plugin("entity.position.get.absolute")
    definition.forward_plugin("entity.position.get.relative")
    definition.forward_plugin("entity.position.set.absolute")
    definition.forward_plugin("entity.position.set.relative")

    definition.forward_plugin("entity.orientation.get.relative")
    definition.forward_plugin("entity.orientation.get.absolute")
    definition.forward_plugin("entity.orientation.set.absolute")
    definition.forward_plugin("entity.orientation.set.absolute")

    definition.forward_plugin("entity.get")

    definition.forward_plugin("entity.parent.get")
    definition.forward_plugin("entity.parent.set")

    definition.forward_plugin("entity.tag.get")
    definition.forward_plugin("entity.tag.set")

    definition.forward_plugin("entity.destroy")
    definition.forward_plugin("entity.spawn")

    definition.forward_plugin("entity.register_destructor")

factory = definition.build("BindEntity")


class EntityEnvironmentClass(factory.create_environment_class()):

    def __init__(self, context):
        super().__init__(context)

        self._hive = hive.get_run_hive()

        # Add reference to this hive for this entity
        if "entity" in context.config:
            self._entity = context.config["entity"]
            register_destructor = context.plugins['entity.register_destructor']
            register_destructor(self._entity, self.destroy)

    def destroy(self):
        self._hive.on_stopped()

    def get_bound_entity(self):
        return self._entity


@factory.builds_environment
def build_entity_environment(cls, i, ex, args, meta_args):
    """Runtime event environment for instantiated hive.

    Provides appropriate sockets and plugins for event interface
    """
    if meta_args.bind_meta_args.bind_entity == "bound":
        ex.get_bound_entity = hive.plugin(cls.get_bound_entity, identifier="entity.get_bound")


EntityEnvironment = hive.meta_hive("EntityEnvironment", build_entity_environment, factory.environment_declarator,
                                   cls=EntityEnvironmentClass)


class EntityCls(factory.create_external_class()):

    def __init__(self):
        super().__init__()

        self._hive = hive.get_run_hive()
        self.entity = None

    def get_config(self):
        config = {}

        if hasattr(self._hive, 'entity'):
            self._hive.entity()
            config['entity'] = self.entity

        return config


@factory.builds_external
def build_bind(cls, i, ex, args, meta_args):
    bind_mode = meta_args.bind_entity

    if bind_mode == 'bound':
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)


BindEntity = hive.dyna_hive("BindEntity", build_bind, declarator=factory.external_declarator, cls=EntityCls)


def get_environment(meta_args):
    if meta_args.bind_entity != 'none':
        return EntityEnvironment

    return None


bind_info = BindInfo("entity", BindEntity, get_environment)
