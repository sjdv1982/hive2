from gui.utils import get_ui_info
from hive.tuple_type import types_match


class NodeIOPin:

    def __init__(self, node, name, data_type, mode, io_type):
        self.node = node
        self.name = name
        self.data_type = data_type
        self.mode = mode
        self.io_type = io_type

        self.targets = set()

    def connect(self, other_pin):
        if not types_match(other_pin.data_type, self.data_type, allow_none=True):
            raise TypeError("Unsupported data types: {}, {}".format(self.data_type, other_pin.data_type))

        if other_pin.mode != self.mode:
            raise TypeError("Incompatible IO modes: {}, {}".format(self.mode, other_pin.mode))

        # Pull inputs can only have one input
        if self.mode == "pull" and self.io_type == "input" and self.targets:
            raise ValueError("Already connected to input")

        self.targets.add(other_pin)

    def disconnect(self, other_pin):
        assert other_pin in self.targets
        self.targets.remove(other_pin)


class HiveNode:

    def __init__(self, hive, hive_path, unique_id):
        self.hive = hive
        self.hive_class_name = hive._hive_object._hive_parent_class.__name__
        self.hive_path = hive_path

        self.info = get_ui_info(hive)

        self.name = self.hive_class_name
        self.unique_id = unique_id

        self.inputs = {name: NodeIOPin(self, name, info['data_type'], info['mode'], "input") for name, info in
                       self.info['inputs'].items()}

        self.outputs = {name: NodeIOPin(self, name, info['data_type'], info['mode'], "output") for name, info in
                        self.info['outputs'].items()}

        self.position = [0.0, 0.0]

    def copy(self, unique_id):
        # TODO it's possible that if we don't touch the hive, no copy is needed!
        new_hive = self.hive._hive_object.instantiate()
        return self.__class__(new_hive, self.hive_path, unique_id)

    def __repr__(self):
        return "<HiveNode ({}): {}>".format(self.unique_id, self.name)