import hive

from ..bind import BindInfo, BindClassDefinition


definition = BindClassDefinition()
bind_mode_param = definition.parameter("bind_entity", "str", 'bound', {'none', 'bound', 'unbound'})


with definition.condition(bind_mode_param != "none"):
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

    definition.forward_plugin("entity.visibility.get")
    definition.forward_plugin("entity.visibility.set")

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

    def get_bound_pos_abs(self):
        return self._plugins["entity.bound.position.get.absolute"](self._entity)

    def get_bound_pos_rel(self, other):
        return self._plugins["entity.bound.position.get.relative"](self._entity, other)

    def get_bound_ori_abs(self):
        return self._plugins["entity.bound.orientation.get.absolute"](self._entity)

    def get_bound_ori_rel(self, other):
        return self._plugins["entity.bound.orientation.get.relative"](self._entity, other)

    def set_bound_pos_abs(self, position):
        self._plugins["entity.bound.position.set.absolute"](self._entity, position)

    def set_bound_pos_rel(self, other, position):
        self._plugins["entity.bound.position.set.relative"](self._entity, other, position)

    def set_bound_ori_abs(self, orientation):
        self._plugins["entity.bound.orientation.set.absolute"](self._entity, orientation)

    def set_bound_ori_rel(self, other, orientation):
        self._plugins["entity.bound.orientation.set.relative"](self._entity, other, orientation)

    def get_bound_tag(self, name):
        return self._plugins['entity.tag.get'](self._entity, name)

    def set_bound_tag(self, name, value):
        self._plugins['entity.tag.set'](self._entity, name, value)

    def get_bound_parent(self, name):
        return self._plugins['entity.parent.get'](self._entity, name)

    def set_bound_parent(self, name, value):
        self._plugins['entity.parent.set'](self._entity, name, value)

    def get_bound_visibility(self, name):
        return self._plugins['entity.visibility.get'](self._entity, name)

    def set_bound_visibility(self, name, value):
        self._plugins['entity.visibility.set'](self._entity, name, value)

    def bound_destroy(self):
        self._plugins['entity.bound.destroy']()


@factory.builds_environment
def build_entity_environment(cls, i, ex, args, meta_args):
    """Runtime event environment for instantiated hive.

    Provides appropriate sockets and plugins for event interface
    """
    if meta_args.bind_meta_args.bind_entity != "bound":
        return

    ex.get_bound_entity = hive.plugin(cls.get_bound_entity, "entity.get_bound")

    ex.get_bound_position_absolute = hive.plugin(cls.get_bound_pos_abs, "entity.bound.position.get.absolute")
    ex.set_bound_position_absolute = hive.plugin(cls.set_bound_pos_abs, "entity.bound.position.set.absolute")
    ex.get_bound_position_relative = hive.plugin(cls.get_bound_pos_rel, "entity.bound.position.get.relative")
    ex.set_bound_position_relative = hive.plugin(cls.set_bound_pos_rel, "entity.bound.position.set.relative")

    ex.get_bound_orientation_absolute = hive.plugin(cls.get_bound_ori_abs, "entity.bound.orientation.get.absolute")
    ex.set_bound_orientation_absolute = hive.plugin(cls.set_bound_ori_abs, "entity.bound.orientation.set.absolute")
    ex.get_bound_orientation_relative = hive.plugin(cls.get_bound_ori_rel, "entity.bound.orientation.get.relative")
    ex.set_bound_orientation_relative = hive.plugin(cls.set_bound_ori_rel, "entity.bound.orientation.set.relative")

    ex.get_bound_parent = hive.plugin(cls.get_bound_parent, "entity.bound.parent.get")
    ex.set_bound_parent = hive.plugin(cls.set_bound_parent, "entity.bound.parent.set")

    ex.get_bound_tag = hive.plugin(cls.get_bound_tag, "entity.bound.tag.get")
    ex.set_bound_tag = hive.plugin(cls.set_bound_tag, "entity.bound.tag.set")

    ex.get_bound_visibility = hive.plugin(cls.get_bound_visibility, "entity.bound.visibility.get")
    ex.set_bound_visibility = hive.plugin(cls.set_bound_visibility, "entity.bound.visibility.set")

    ex.bound_destroy = hive.plugin(cls.bound_destroy, "entity.bound.destroy")


EntityEnvironment = hive.meta_hive("EntityEnvironment", build_entity_environment, factory.environment_declarator,
                                    builder_cls=EntityEnvironmentClass)


class EntityCls(factory.create_external_class()):

    def __init__(self):
        super().__init__()

        self._hive = hive.get_run_hive()
        self.entity = None

    def get_config(self):
        if hasattr(self._hive, 'entity'):
            self._hive.entity()
            return dict(entity=self.entity)

        return {}


@factory.builds_external
def build_bind(cls, i, ex, args, meta_args):
    bind_mode = meta_args.bind_entity

    if bind_mode == 'bound':
        i.entity = hive.property(cls, "entity", "entity")
        i.pull_entity = hive.pull_in(i.entity)
        ex.entity = hive.antenna(i.pull_entity)


BindEntity = hive.dyna_hive("BindEntity", build_bind, declarator=factory.external_declarator, builder_cls=EntityCls)


def get_environment(meta_args):
    if meta_args.bind_entity != 'none':
        return EntityEnvironment

    return None


bind_info = BindInfo("entity", BindEntity, get_environment)
