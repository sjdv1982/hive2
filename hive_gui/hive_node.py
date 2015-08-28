from .utils import get_io_info

from hive.tuple_type import types_match


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
            raise TypeError("Incompatible data types: {}, {}".format(self.data_type, other_pin.data_type))

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

    def __init__(self, hive_object, hive_path, name, params):
        """
        Container for GUI configuration of HiveObject instance

        :param hive_object: HiveObject instance
        :param hive_path: path to import Hive class
        :param name: name of GUI node
        :param params: parameter dictionary containing meta_args, args and cls_args data
        :return:
        """

        # Warning - args and cls_args of hive_object might not correspond to params
        # Altering the params dict from the UI is safe as it won't affect the pinout on the hiveobject
        # Use the params dict instead of re-scraping the hive_object if reading these values
        self.hive_object = hive_object
        self.hive_path = hive_path

        self.io_info = get_io_info(hive_object)
        self.params = params

        self.name = name
        self.docstring = hive_object.__doc__ or ""

        self.inputs = {name: NodeIOPin(self, name, info['data_type'], info['mode'], "input")
                       for name, info in self.io_info['inputs'].items()}

        self.outputs = {name: NodeIOPin(self, name, info['data_type'], info['mode'], "output")
                        for name, info in self.io_info['outputs'].items()}

        self.pin_order = self.io_info['pin_order']

        self.position = (0.0, 0.0)
        self.folded = False

    def __repr__(self):
        return "<HiveNode ({})>".format(self.name)