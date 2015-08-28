from .utils import get_io_info
from .sockets import get_colour, get_shape

from collections import OrderedDict
from hive.tuple_type import types_match


class IOPin(object):

    def __init__(self, node, name, data_type, mode, io_type):
        self.node = node
        self.name = name

        self.colour = get_colour(data_type)
        self.shape = get_shape(mode)

        self.io_type = io_type
        self.targets = set()

        self.is_folded = False

        self.data_type = data_type
        self.mode = mode

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


class GUINode(object):
    inputs = None
    outputs = None
    position = None
    pin_order = None
    name = None
    tooltip = ""


class BeeNode(GUINode):

    def __init__(self, import_path, name, io_type, data_type, mode):
        """
        Container for GUI configuration of IO Bee (antenna / output)

        :param import_path: path to import bee
        :param name: name of GUI node
        :param io_type: bee io type
        :param data_type: pin data type
        :param mode: pin mode
        :return:
        """
        self.name = name
        self.import_path = import_path

        self.inputs = {}
        self.outputs = {}
        self.pin_order = []

        if io_type == "output":
            self.inputs["output"] = IOPin(self, "output", data_type, mode, "input")
            self.pin_order.append("output")

        elif io_type == "antenna":
            self.outputs["antenna"] = IOPin(self, "antenna", data_type, mode, "output")
            self.pin_order.append("antenna")

        else:
            raise ValueError(io_type)


class HiveNode(GUINode):

    def __init__(self, hive_object, import_path, name, params):
        """
        Container for GUI configuration of HiveObject instance

        :param hive_object: HiveObject instance
        :param import_path: path to import Hive class
        :param name: name of GUI node
        :param params: parameter dictionary containing meta_args, args and cls_args data
        :return:
        """
        self.name = name

        # Warning - args and cls_args of hive_object might not correspond to params
        # Altering the params dict from the UI is safe as it won't affect the pinout on the hiveobject
        # Use the params dict instead of re-scraping the hive_object if reading these values
        self.import_path = import_path
        self.params = params

        io_info = get_io_info(hive_object)

        self.tooltip = hive_object.__doc__ or ""
        self.pin_order = io_info['pin_order']
        self.inputs = OrderedDict((name, IOPin(self, name, info['data_type'], info['mode'], "input"))
                                  for name, info in io_info['inputs'].items())

        self.outputs = OrderedDict((name, IOPin(self, name, info['data_type'], info['mode'], "output"))
                                   for name, info in io_info['outputs'].items())

        self.position = (0.0, 0.0)

    def __repr__(self):
        return "<HiveNode ({})>".format(self.name)