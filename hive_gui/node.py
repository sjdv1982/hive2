from .utils import get_io_info
from .sockets import get_colour, get_shape
from .iterable_view import ListView

from collections import OrderedDict
from hive.tuple_type import types_match


class IOPin(object):

    def __init__(self, node, name, data_type, mode, io_type):
        self.name = name

        self._node = node
        self._colour = get_colour(data_type)
        self._shape = get_shape(mode)
        self._io_type = io_type
        self._data_type = data_type
        self._is_trigger = types_match(("trigger",), data_type, allow_none=False)

        self._mode = mode # "any" for any connection
        self._current_mode = mode

        self._targets = []
        self._max_targets = -1
        self.targets = ListView(self._targets)

        self.is_folded = False

        if mode == "pull" and io_type == "input":
            self._max_targets = 1

    @property
    def data_type(self):
        return self._data_type

    @property
    def node(self):
        return self._node

    @property
    def colour(self):
        return self._colour

    @property
    def shape(self):
        return self._shape

    @property
    def io_type(self):
        return self._io_type

    @property
    def data_type(self):
        return self._data_type

    @property
    def mode(self):
        return self._mode

    @property
    def current_mode(self):
        return self._current_mode

    @property
    def max_connections(self):
        return self._max_targets

    def can_connect(self, other_pin):
        # Check types match. If trigger, other must be trigger too.
        if not types_match(other_pin.data_type, self._data_type, allow_none=not self._is_trigger):
            return False

        if other_pin.mode != "any" and self._mode != "any":
            if other_pin.mode != self._mode:
                return False

        # Pull inputs can only have one input
        if len(self._targets) == self._max_targets:
            return False

        return True

    def connect_target(self, other):
        assert other not in self._targets
        self._targets.append(other)

    def disconnect_target(self, other):
        self._targets.remove(other)

    def reorder_target(self, other, index):
        current_index = self._targets.index(other)
        if index > current_index:
            index -= 1

        del self._targets[current_index]
        self._targets.insert(index, other)

    def __repr__(self):
        return "<{} pin {}.{}>".format(self._io_type, self._node.name, self.name)


class BeeIOPin(IOPin):

    def __init__(self, node, name, data_type, mode, io_type):
        super().__init__(node, name, data_type, mode, io_type)

        self._max_targets = 1

    def mimic_other_pin(self, other):
        # Update cosmetics for other
        self._shape = other.shape
        self._colour = other.colour
        self._current_mode = other.mode

    def connect_target(self, other):
        super().connect_target(other)

        self.mimic_other_pin(other)

    def can_connect(self, other_pin):
        if not super().can_connect(other_pin):
            return False

        return not isinstance(other_pin, self.__class__)


class GUINode(object):
    _import_path = None
    _tooltip = ""

    inputs = None
    outputs = None
    position = None
    pin_order = None
    name = None
    params = {}

    @property
    def import_path(self):
        return self._import_path

    @property
    def tooltip(self):
        return self._tooltip


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
        self.position = (0.0, 0.0)

        self.inputs = {}
        self.outputs = {}
        self.pin_order = []

        # Read only
        self._import_path = import_path

        # GUI data used to support interoperability with other nodes
        self._data_type = data_type
        self._mode = mode

        # Technically lazy, these aren't meta params, but we're just going to cheat
        self.params = {'meta_args': {'data_type': data_type, 'mode': mode}}

        if io_type == "output":
            pin_name = "output"
            self.inputs[pin_name] = BeeIOPin(self, pin_name, data_type, mode, "input")
            self.pin_order.append(pin_name)

        elif io_type == "input":
            pin_name = "input"
            self.outputs[pin_name] = BeeIOPin(self, pin_name, data_type, mode, "output")
            self.pin_order.append(pin_name)

        else:
            raise ValueError(io_type)

    @property
    def data_type(self):
        return self._data_type

    @property
    def mode(self):
        return self._mode

    def __repr__(self):
        return "<Bee Node ({})>".format(self.name)


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

        # Read only
        self._tooltip = hive_object.__doc__ or ""
        self._import_path = import_path

        # Warning - args and cls_args of hive_object might not correspond to params
        # Altering the params dict from the UI is safe as it won't affect the pinout on the hiveobject
        # Use the params dict instead of re-scraping the hive_object if reading these values
        self.params = params

        # Pin IO
        io_info = get_io_info(hive_object)
        self.pin_order = io_info['pin_order']
        self.inputs = OrderedDict((name, IOPin(self, name, info['data_type'], info['mode'], "input"))
                                  for name, info in io_info['inputs'].items())

        self.outputs = OrderedDict((name, IOPin(self, name, info['data_type'], info['mode'], "output"))
                                   for name, info in io_info['outputs'].items())

        self.position = (0.0, 0.0)

    def __repr__(self):
        return "<HiveNode ({})>".format(self.name)