import hive


class TagClass:

    def __init__(self):
        self._get_tag = None
        self._set_tag = None

        self._get_entity_id = None
        self.entity_id = None

        self.tag_name = None
        self.tag_value = None

    def set_get_tag(self, get_tag):
        self._get_tag = get_tag

    def set_set_tag(self, set_tag):
        self._set_tag = set_tag

    def set_get_entity_id(self, get_entity_id):
        self._get_entity_id = get_entity_id

    def get_entity_id(self):
        self.entity_id = self._get_entity_id()

    def get_tag(self):
        self.tag_value = self._get_tag(self.tag_name)

    def set_tag(self):
        self._set_tag(self.tag_name, self.tag_value)


def declare_tag(meta_args):
    meta_args.bound = hive.parameter("bool", True)
    meta_args.mode = hive.parameter("str", "get", options={"get", "set"})
    meta_args.data_type = hive.parameter("str", "int")


def build_tag(cls, i, ex, args, meta_args):
    """Access to entity tag API"""
    if meta_args.bound:
        ex.get_bound = hive.socket(cls.set_get_entity_id, identifier="entity.get_bound")
        i.do_get_bound_entity_id = hive.triggerable(cls.get_entity_id)

    else:
        i.entity_id = hive.property(cls, "entity_id", "int.entity_id")
        i.pull_entity_id = hive.pull_in(i.entity_id)
        ex.entity_id = hive.antenna(i.pull_entity_id)
        i.do_get_bound_entity_id = hive.triggerable(i.pull_entity_id)

    i.tag_name = hive.property(cls, "tag_name", "str")
    i.tag_value = hive.property(cls, "tag_value", meta_args.data_type)

    i.pull_tag_name = hive.pull_in(i.tag_name)
    ex.name = hive.antenna(i.pull_tag_name)

    if meta_args.mode == 'get':
        ex.get_get_tag = hive.socket(cls.set_get_tag, identifier="entity.tag.get")

        i.pull_tag_value = hive.pull_out(i.tag_value)
        ex.value = hive.output(i.pull_tag_value)

        i.do_get_tag = hive.triggerable(cls.get_tag)

        hive.trigger(i.pull_tag_value, i.do_get_bound_entity_id)
        hive.trigger(i.pull_tag_value, i.pull_tag_name)
        hive.trigger(i.pull_tag_value, i.do_get_tag)

    else:
        ex.get_set_tag = hive.socket(cls.set_set_tag, identifier="entity.tag.set")

        i.push_tag_value = hive.push_in(i.tag_value)
        ex.value = hive.antenna(i.push_tag_value)

        i.do_get_tag = hive.triggerable(cls.get_tag)

        hive.trigger(i.push_tag_value, i.do_get_bound_entity_id)
        hive.trigger(i.push_tag_value, i.pull_tag_name)
        hive.trigger(i.push_tag_value, i.do_get_tag)


Tag = hive.dyna_hive("Tag", build_tag, declare_tag, TagClass)