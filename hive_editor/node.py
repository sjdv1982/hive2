from collections import OrderedDict

from hive.identifiers import identifiers_match
from .data_views import ListView, DictView
from .sockets import get_colour, get_shape
from .protected_container import ProtectedContainer, RestrictedAttribute, RestrictedProperty

FOLD_NODE_IMPORT_PATH = "dragonfly.std.Variable"


class MimicFlags(object):
    NONE = 0
    COLOUR = 1
    SHAPE = 2


PIN_MODES = {'pull', 'push', 'any'}
IO_TYPES = {'input', 'output'}


class IOPin(ProtectedContainer):

    def __init__(self, node, name, io_type, data_type, mode="pull", max_connections=-1, restricted_types=None,
                 mimic_flags=MimicFlags.NONE, is_virtual=False, count_proxies=False):
        assert io_type in IO_TYPES, "Invalid io type for pin: '{}".format(io_type)
        assert mode in PIN_MODES, "Invalid mode for pin: '{}'".format(mode)

        # Non-permitted connection types
        if restricted_types is None:
            restricted_types = []

        # Pull rule
        if mode == "pull" and io_type == "input":
            max_connections = 1

        # Mimicking pins
        if mode == "any":
            if not -1 < max_connections <= 1:
                max_connections = 1

            mimic_flags |= MimicFlags.SHAPE

        # Read only
        with self.make_writable():
            self.is_folded = False

        self._name = name
        self._colour = get_colour(data_type)
        self._data_type = data_type
        self._mode = mode
        self._is_trigger = identifiers_match(data_type, "trigger", support_untyped=False)
        self._io_type = io_type
        self._node = node
        self._restricted_data_types = restricted_types
        self._shape = get_shape(mode)
        self._mimic_flags = mimic_flags
        self._is_virtual = is_virtual

        self._connections = []
        self._connection_count = 0
        self._count_proxies = count_proxies
        self._max_connections = max_connections

    # Read only view
    is_folded = RestrictedAttribute()

    @property
    def name(self):
        return self._name

    @property
    def connections(self):
        return ListView(self._connections)

    @property
    def is_trigger(self):
        return self._is_trigger

    @property
    def data_type(self):
        return self._data_type

    @property
    def is_virtual(self):
        """Whether pin is actually a connectable pin"""
        return self._is_virtual

    @property
    def node(self):
        return self._node

    @property
    def mode(self):
        return self._mode

    @property
    def shape(self):
        return self._shape

    @property
    def colour(self):
        return self._colour

    @property
    def io_type(self):
        return self._io_type

    @property
    def data_type(self):
        return self._data_type

    @property
    def max_connections(self):
        return self._max_connections

    @property
    def mimic_flags(self):
        return self._mimic_flags

    @property
    def is_foldable(self):
        if self.is_folded:
            return False

        # Only hives support folding
        if self.is_virtual:
            return False

        if self.io_type != "input":
            return False

        if self.mode != "pull":
            return False

        if not self.connections:
            return True

        if len(self.connections) == 1:
            target_connection = next(iter(self.connections))
            target_pin = target_connection.output_pin

            # Only allow variables to be folded
            return target_pin.node.is_foldable

        return False

    def can_connect_to(self, other_pin, is_source):
        # If a restricted data type
        for data_type in self._restricted_data_types:
            if identifiers_match(other_pin.data_type, data_type, support_untyped=False):
                return False

        # Limit connections if provided
        if self._connection_count == self._max_connections:
            return False

        return True

    def mimic_other_pin(self, other_pin):
        # Update cosmetics for other
        flags = self._mimic_flags

        if flags & MimicFlags.SHAPE:
            self._shape = other_pin.shape

        if flags & MimicFlags.COLOUR:
            self._colour = other_pin.colour

    def unmimic_other_pin(self, other_pin):
        pass

    def add_connection(self, connection):
        assert connection not in self._connections
        self._connections.append(connection)

        if connection.output_pin is self:
            other_pin = connection.input_pin
        else:
            other_pin = connection.output_pin

        if self._count_proxies or not other_pin.is_virtual:
            self._connection_count += 1

        # Mimic aesthetics
        self.mimic_other_pin(other_pin)

    def remove_connection(self, connection):
        self._connections.remove(connection)

        # Post connection
        if connection.output_pin is self:
            other_pin = connection.input_pin
        else:
            other_pin = connection.output_pin

        if self._count_proxies or not other_pin.is_virtual:
            self._connection_count -= 1

        self.unmimic_other_pin(other_pin)

    def reorder_target(self, connection, index):
        current_index = self._connections.index(connection)
        del self._connections[current_index]
        self._connections.insert(index, connection)

    def __repr__(self):
        return "<{} pin {}.{}>".format(self._io_type, self._node.name, self.name)


class NodeTypes(object):
    HIVE, BEE, HELPER = range(3)


class Node(ProtectedContainer):

    def __init__(self, name, node_type, import_path, params, params_info):
        """
        Container for GUI configuration of HiveObject instance

        :param name: unique node name
        :param import_path: path to find object representing node (may not exist for certain node types)
        :param params: parameter dictionary containing data about node
        :param params_info: parameter dictionary containing data about params dict
        :return:
        """
        super(Node, self).__init__()

        with self.make_writable():
            self.name = name
            self.tooltip = ""
            self.position = (0.0, 0.0)

        # Read only
        self._node_type = node_type
        self._import_path = import_path

        self._params = params
        self._params_info = params_info

        # Pin IO
        self._pin_order = []
        self._inputs = OrderedDict()
        self._outputs = OrderedDict()

    def add_input(self, name, data_type=None, mode="pull", max_connections=-1, restricted_types=None,
                  mimic_flags=MimicFlags.NONE, is_virtual=False, count_proxies=False):
        pin = IOPin(self, name, "input", data_type, mode, max_connections, restricted_types, mimic_flags,
                    is_virtual, count_proxies)
        self._inputs[name] = pin
        self._pin_order.append(name)
        return pin

    def add_output(self, name, data_type=None, mode="pull", max_connections=-1, restricted_types=None,
                   mimic_flags=MimicFlags.NONE, is_virtual=False, count_proxies=False):
        pin = IOPin(self, name, "output", data_type, mode, max_connections, restricted_types, mimic_flags,
                    is_virtual, count_proxies)
        self._outputs[name] = pin
        self._pin_order.append(name)
        return pin

    @property
    def import_path(self):
        return self._import_path

    @property
    def node_type(self):
        return self._node_type

    @property
    def inputs(self):
        return DictView(self._inputs)

    @property
    def outputs(self):
        return DictView(self._outputs)

    @property
    def pin_order(self):
        return ListView(self._pin_order)

    @RestrictedProperty
    def params(self):
        return DictView({k: DictView(v) for k, v in self._params.items()})

    @params.restricted_getter
    def params(self):
        return self._params

    @property
    def params_info(self):
        return DictView({k: DictView(v) for k, v in self._params_info.items()})

    @property
    def is_folded(self):
        for output_pin in self._outputs.values():
            for connection in output_pin.connections:
                if connection.input_pin.is_folded:
                    return True
        return False

    @property
    def is_foldable(self):
        if self.is_folded:
            return False

        all_connections = sum(len(p.connections) for p in self._outputs.values())
        all_connections += sum(len(p.connections) for p in self._inputs.values())

        # If other pin is in use else where
        return all_connections <= 1

    position = RestrictedAttribute()
    name = RestrictedAttribute()
    tooltip = RestrictedAttribute()

    def __repr__(self):
        return "<HiveNode ({})>".format(self.name)
