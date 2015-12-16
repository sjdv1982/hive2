from .connection import Connection, ConnectionType
from .factory import BeeNodeFactory, HiveNodeFactory
from .history import OperationHistory
from .inspector import HiveNodeInspector, BeeNodeInspector
from .models import model
from .node import FOLD_NODE_IMPORT_PATH
from .node_io import HiveMapIO
from .utils import start_value_from_type, is_identifier, \
    camelcase_to_underscores


def _get_unique_name(existing_names, base_name):
    """Find unique value of base name which may have a number appended to the end

    :param existing_names: names currently in use
    :param base_name: base of name to use
    """
    i = 0
    while True:
        name = "{}_{}".format(base_name, i)
        if name not in existing_names:
            return name

        i += 1


class NodeConnectionError(Exception):
    pass


class NodeManager(object):

    def __init__(self):
        self.history = OperationHistory()

        self.bee_node_factory = BeeNodeFactory()
        self.hive_node_factory = HiveNodeFactory()

        self.hive_node_inspector = HiveNodeInspector()
        self.bee_node_inspector = BeeNodeInspector(self._find_attributes)

        self.docstring = ""
        self.nodes = {}

        self._clipboard = None

        self.on_node_created = None
        self.on_node_destroyed = None
        self.on_node_moved = None
        self.on_node_renamed = None

        self.on_connection_created = None
        self.on_connection_destroyed = None
        self.on_connection_reordered = None

        self.on_pin_folded = None
        self.on_pin_unfolded = None

        self.on_pasted_pre_connect = None

    def _unique_name_from_import_path(self, import_path):
        obj_name = import_path.split(".")[-1]
        as_variable = camelcase_to_underscores(obj_name)
        return _get_unique_name(self.nodes, as_variable)

    def _find_attributes(self):
        return {name: node for name, node in self.nodes.items() if node.import_path == "hive.attribute"}

    def _add_connection(self, connection):
        """Connect connection and push to history.

        :param connection: connection to connect
        """
        self.history.push_operation(self._add_connection, (connection,),
                                    self.delete_connection, (connection,))

        connection.connect()

        # Ask GUI to perform connection
        if callable(self.on_connection_created):
            self.on_connection_created(connection)

        output_pin = connection.output_pin
        input_pin = connection.input_pin
        print("Create connection", output_pin.name, output_pin.node, input_pin.name, input_pin.node)

    def create_connection(self, output_pin, input_pin):
        """Create connection between two pins.

        :param output_pin: output pin from which the connection originates
        :param input_pin: input pin at which the connection is completed
        """
        # Check pin isn't folded
        if input_pin.is_folded:
            raise NodeConnectionError("Cannot connect to a folded pin")

        # Check connection is permitted
        result = Connection.is_valid_between(output_pin, input_pin)

        if result == ConnectionType.INVALID:
            raise NodeConnectionError("Can't connect {} to {}".format(output_pin, input_pin))

        connection = Connection(output_pin, input_pin, is_trigger=(result == ConnectionType.TRIGGER))

        # Must call connection.connect()
        self._add_connection(connection)

    def delete_connection(self, connection):
        """Delete connection and write to history.

        :param connection: connection object
        """
        # Ask GUI to perform connection
        if callable(self.on_connection_destroyed):
            self.on_connection_destroyed(connection)

        print("Delete Connection", connection)

        connection.delete()

        self.history.push_operation(self.delete_connection, (connection,),
                                    self._add_connection, (connection,))

    def reorder_connection(self, connection, index):
        """Change connection order relative to other connections for the output pin.

        :param connection: connection object
        :param index: new connection index
        """
        output_pin = connection.output_pin
        old_index = output_pin.connections.index(connection)

        output_pin.reorder_target(connection, index)

        # Ask GUI to reorder connection
        if callable(self.on_connection_reordered):
            self.on_connection_reordered(connection, index)

        self.history.push_operation(self.reorder_connection, (connection, index),
                                    self.reorder_connection, (connection, old_index))

    def _add_node(self, node):
        """Add node to node dict and write to history.

        :param node: node to add
        """
        self.nodes[node.name] = node

        if callable(self.on_node_created):
            self.on_node_created(node)

        for pin in node.inputs.values():
            assert not pin.is_folded, (pin.name, pin.node)

        self.history.push_operation(self._add_node, (node,), self.delete_node, (node,))

    def create_bee(self, import_path, params=None):
        """Create a bee node with the given import path"""
        if params is None:
            params = {}

        name = self._unique_name_from_import_path(import_path)
        param_info = self.bee_node_inspector.inspect_configured(import_path, params)
        node = self.bee_node_factory.new(name, import_path, params, param_info)

        self._add_node(node)
        return node

    def create_hive(self, import_path, params=None):
        """Create a hive node with the given path"""
        if params is None:
            params = {}

        name = self._unique_name_from_import_path(import_path)

        try:
            param_info = self.hive_node_inspector.inspect_configured(import_path, params)

        except Exception:
            print("Failed to inspect '{}'".format(import_path))
            raise

        try:
            node = self.hive_node_factory.new(name, import_path, params, param_info)

        except Exception:
            print("Failed to instantiate '{}'".format(import_path))
            raise

        self._add_node(node)
        return node

    def delete_node(self, node):
        # Remove connections
        for input_pin in node.inputs.values():
            is_folded = input_pin.is_folded

            # Handle folded nodes
            if is_folded:
                self.unfold_pin(input_pin)
                output_pin = next(iter(input_pin.connections)).output_pin

            for connection in list(input_pin.connections):
                self.delete_connection(connection)

            # Delete folded nodes (only should be one folded node!)
            if is_folded:
                self.delete_node(output_pin.node)

        for output_pin in node.outputs.values():
            for connection in list(output_pin.connections):
                self.delete_connection(connection)

        if callable(self.on_node_destroyed):
            self.on_node_destroyed(node)

        self.nodes.pop(node.name)

        self.history.push_operation(self.delete_node, (node,), self._add_node, (node,))

    def set_node_name(self, node, name, attempt_till_success=False):
        if not is_identifier(name):
            raise ValueError("Name must be valid python identifier: {}".format(name))

        if self.nodes.get(name, node) is not node:
            # Try till we succeed
            if attempt_till_success:
                name = _get_unique_name(self.nodes, name)

            else:
                raise ValueError("Can't rename {} to {}".format(node, name))

        # Change key
        old_name = node.name

        self.nodes.pop(old_name)
        self.nodes[name] = node

        # Update name
        node.name = name

        if callable(self.on_node_renamed):
            self.on_node_renamed(node, name)

        self.history.push_operation(self.set_node_name, (node, name), self.set_node_name, (node, old_name))

    def set_node_position(self, node, position):
        old_position = node.position
        node.position = position

        # Move folded nodes too
        dx = position[0] - old_position[0]
        dy = position[1] - old_position[1]

        for pin in node.inputs.values():
            if pin.is_folded:
                target_connection = next(iter(pin.connections))
                target_pin = target_connection.output_pin
                other_node = target_pin.node

                new_position = other_node.position[0] + dx, other_node.position[1] + dy
                self.set_node_position(other_node, new_position)

        if callable(self.on_node_moved):
            self.on_node_moved(node, position)

        self.history.push_operation(self.set_node_position, (node, position),
                                    self.set_node_position, (node, old_position))

    def fold_pin(self, pin):
        assert pin.is_foldable

        # Create variable
        if not pin.connections:
            # TODO take start value from pin bee?
            params = dict(meta_args=dict(data_type=pin.data_type),
                          args=dict(start_value=start_value_from_type(pin.data_type)))

            # Create variable node, attempt to call it same as pin
            target_node = self.create_hive(FOLD_NODE_IMPORT_PATH, params)
            target_pin = next(iter(target_node.outputs.values()))

            self.set_node_name(target_node, pin.name, attempt_till_success=True)
            self.create_connection(target_pin, pin)

            # TODO account for width of node and auto-arrange

        pin.is_folded = True

        if callable(self.on_pin_folded):
            self.on_pin_folded(pin)

        self.history.push_operation(self.fold_pin, (pin,), self.unfold_pin, (pin,))

    def unfold_pin(self, pin):
        assert pin.is_folded
        assert pin.connections

        pin.is_folded = False

        if callable(self.on_pin_unfolded):
            self.on_pin_unfolded(pin)

        self.history.push_operation(self.unfold_pin, (pin,), self.fold_pin, (pin,))

    def to_string(self):
        hivemap = self.export_hivemap()
        return str(hivemap)

    def from_string(self, data):
        # Validate type
        if not isinstance(data, str):
            raise TypeError("Loaded data should be a string type, not {}".format(type(data)))

        # Read hivemap
        hivemap = model.Hivemap(data)
        self.load_hivemap(hivemap)

    def export_hivemap(self):
        hivemap_io = HiveMapIO()
        hivemap_io.save(self, docstring=self.docstring)

        return hivemap_io.hivemap

    def load_hivemap(self, hivemap):
        with self.history.composite_operation("load"):
            # Clear nodes first
            for node in list(self.nodes.values()):
                self.delete_node(node)

            hivemap_io = HiveMapIO(hivemap)
            data = hivemap_io.load(self)

            self.docstring = data['docstring']

    def cut(self, nodes):
        with self.history.composite_operation("cut"):
            self.copy(nodes)

            # Delete nodes
            for node in nodes:
                self.delete_node(node)

    def copy(self, nodes):
        """Copy nodes to clipboard

        :param nodes: nodes to copy
        """
        with_folded_nodes = set(nodes)

        # Find nodes that are internally folded
        for node in nodes:
            for pin in node.inputs.values():
                if pin.is_folded:
                    target_connection = next(iter(pin.connections))
                    target_pin = target_connection.output_pin
                    target_node = target_pin.node
                    with_folded_nodes.add(target_node)

        hivemap_io = HiveMapIO()
        hivemap_io.save(self, nodes=with_folded_nodes)

        self._clipboard = hivemap_io

    def paste(self, position):
        """Paste nodes from clipboard

        :param position: position of target center of mass of nodes
        """
        with self.history.composite_operation("paste"):
            data = self._clipboard.load(self)
            node_map = data['nodes']

            if not node_map:
                return

            names, nodes = zip(*node_map.items())

            # Find midpoint
            average_x = 0.0
            average_y = 0.0

            for node in nodes:
                average_x += node.position[0]
                average_y += node.position[1]

            average_x /= len(nodes)
            average_y /= len(nodes)

            # Displacement to the center
            offset_x = position[0] - average_x
            offset_y = position[1] - average_y

            # Move nodes to mouse position
            for node in nodes:
                position = node.position[0] + offset_x, node.position[1] + offset_y
                self.set_node_position(node, position)
