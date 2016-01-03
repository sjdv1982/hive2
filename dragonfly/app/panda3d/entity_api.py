import hive


class EntityClass:

    def __init__(self):
        self._entities = []
        self._entity_hive_destructors = {}

        self._templates = {}

    def set_absolute_position(self, entity, position):
        entity.set_pos(entity.get_top(), position)

    def set_relative_position(self, entity, other_entity, position):
        entity.set_pos(other_entity, position)

    def get_absolute_position(self, entity):
        return entity.get_pos(entity.get_top())

    def get_relative_position(self, entity, other_entity):
        return entity.get_pos(other_entity)

    def set_absolute_orientation(self, entity, orientation):
        p, r, h = orientation
        entity.set_hpr(entity.get_top(), h, p, r)

    def set_relative_orientation(self, entity, other_entity, orientation):
        p, r, h = orientation
        entity.set_pos(other_entity, h, p, r)

    def get_absolute_orientation(self, entity):
        h, p, r = entity.get_hpr(entity.get_top())
        return p, r, h

    def get_relative_orientation(self, entity, other_entity):
        h, p, r = entity.get_hpr(other_entity)
        return p, r, h

    def set_parent(self, entity, parent):
        entity.wrt_reparent_to(parent)

    def get_parent(self, entity):
        return entity.getParent()

    def set_tag(self, entity, name, value):
        entity.set_python_tag(name, value)

    def get_tag(self, entity, name):
        return entity.get_python_tag(name)

    def spawn_entity(self, class_name):
        entity_template = self._templates[class_name]
        entity = entity_template.copy_to(base.render)
        self._entities.append(entity)
        return entity

    def destroy_entity(self, entity):
        if entity in self._entity_hive_destructors:
            destructors = self._entity_hive_destructors.pop(entity)

            for callback in destructors:
                callback()

        self._entities.remove(entity)

        entity.detach_node()

    def register_hive_destructor(self, entity, destructor):
        self._entity_hive_destructors.setdefault(entity, []).append(destructor)

    def register_entity_template(self, template_name, template):
        self._templates[template_name] = template


def build_entity(cls, i, ex, args):
    ex.set_abs_position = hive.plugin(cls.set_absolute_position, identifier="entity.position.set.absolute",
                                      export_to_parent=True)
    ex.get_abs_position = hive.plugin(cls.get_absolute_position, identifier="entity.position.get.absolute",
                                      export_to_parent=True)

    ex.set_rel_position = hive.plugin(cls.set_relative_position, identifier="entity.position.set.relative",
                                      export_to_parent=True)
    ex.get_rel_position = hive.plugin(cls.get_relative_position, identifier="entity.position.get.relative",
                                      export_to_parent=True)

    ex.set_abs_orientation = hive.plugin(cls.set_absolute_orientation, identifier="entity.orientation.set.absolute",
                                         export_to_parent=True)
    ex.get_abs_orientation = hive.plugin(cls.get_absolute_orientation, identifier="entity.orientation.get.absolute",
                                         export_to_parent=True)

    ex.set_rel_orientation = hive.plugin(cls.set_relative_orientation, identifier="entity.orientation.set.relative",
                                         export_to_parent=True)
    ex.get_rel_orientation = hive.plugin(cls.get_relative_orientation, identifier="entity.orientation.get.relative",
                                         export_to_parent=True)

    ex.set_parent = hive.plugin(cls.set_parent, identifier="entity.parent.set",
                                export_to_parent=True)
    ex.get_parent = hive.plugin(cls.get_parent, identifier="entity.parent.get",
                                export_to_parent=True)

    ex.set_tag = hive.plugin(cls.set_tag, identifier="entity.tag.set",
                             export_to_parent=True)
    ex.get_tag = hive.plugin(cls.get_tag, identifier="entity.tag.get",
                             export_to_parent=True)

    ex.get_entity = hive.plugin(lambda name: None, identifier="entity.get", export_to_parent=True)

    ex.spawn_entity = hive.plugin(cls.spawn_entity, identifier="entity.spawn",
                                  export_to_parent=True)
    ex.destroy_entity = hive.plugin(cls.destroy_entity, identifier="entity.destroy",
                                    export_to_parent=True)
    ex.register_entity_template = hive.plugin(cls.register_entity_template, "entity.register_template",
                                              export_to_parent=True)
    ex.register_hive_destructor = hive.plugin(cls.register_hive_destructor, "entity.register_destructor",
                                              export_to_parent=True)


EntityAPI = hive.hive("EntityAPI", build_entity, cls=EntityClass)