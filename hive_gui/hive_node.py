from .utils import get_io_info, get_post_init_info

from hive.tuple_type import types_match
from collections import OrderedDict


class NodeIOPin(object):

    def __init__(self, node, name, data_type, mode, io_type):
        self.node = node
        self.name = name
        self.data_type = data_type
        self.mode = mode
        self.io_type = io_type
        self.is_folded = False

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

    def __repr__(self):
        return "<{} pin {}.{}>".format(self.io_type, self.node.name, self.name)


class HiveNode(object):

    def __init__(self, hive, hive_path, name):
        self.hive = hive
        self.hive_class_name = hive._hive_object._hive_parent_class.__name__
        self.hive_path = hive_path

        self.io_info = get_io_info(hive)
        self.post_init_info = get_post_init_info(hive)

        self.name = name
        self.docstring = hive.__doc__ or ""

        self.inputs = {name: NodeIOPin(self, name, info['data_type'], info['mode'], "input")
                       for name, info in self.io_info['inputs'].items()}

        self.outputs = {name: NodeIOPin(self, name, info['data_type'], info['mode'], "output")
                        for name, info in self.io_info['outputs'].items()}

        self.pin_order = self.io_info['pin_order']

        self.position = (0.0, 0.0)
        self.folded = False

    def __repr__(self):
        return "<HiveNode ({})>".format(self.name)