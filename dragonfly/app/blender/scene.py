import hive


class SceneClass:

    def __init__(self, scene):
        self._entities = {}
        self._scene = scene

    def get_entity(self, identifier):
        return self._entities[identifier]

    def get_position_absolute(self, entity):
        return tuple(entity.worldPosition)

    def get_orientation_absolute(self, entity):
        return tuple(entity.worldOrientation.to_quaternion())

    def get_position_relative(self, entity, other):
        return tuple(entity.worldPosition - other.worldPosition)

    def get_orientation_relative(self, entity, other):
        return tuple(entity.worldOrientation.to_quaternion().rotation_difference(other.worldPosition.to_quaternion()))

    def spawn_entity(self, class_name, identifier):
        entity = self._scene.addObject(class_name, class_name)
        entity.worldTransform = entity.worldTransform.inverted() * entity.worldTransform

        self._entities[identifier] = entity
        return entity

    def get_scene(self):
        return self._scene


def build_scene(cls, i, ex, args):
    ex.get_entity = hive.plugin(cls.get_entity, identifier=("entity", "get"))
    ex.get_position_absolute = hive.plugin(cls.get_position_absolute, identifier=("entity", "position", "absolute",
                                                                                  "get"))
    ex.get_position_relative = hive.plugin(cls.get_position_relative, identifier=("entity", "position", "relative",
                                                                                  "get"))
    ex.get_orientation_absolute = hive.plugin(cls.get_orientation_absolute, identifier=("entity", "orientation",
                                                                                        "absolute", "get"))
    ex.get_orientation_relative = hive.plugin(cls.get_orientation_relative, identifier=("entity", "orientation",
                                                                                        "relative", "get"))
    ex.spawn_entity = hive.plugin(cls.spawn_entity, identifier=("entity", "spawn"))
    ex.get_scene = hive.plugin(cls.get_scene, identifier=("scene", "get_current"))

Scene = hive.hive("Scene", build_scene, cls=SceneClass)
