import logging
from keyword import iskeyword

from .code_generator import dict_to_parameter_array, parameter_array_to_dict
from .connection import Connection, ConnectionType
from .factory import BeeNodeFactory, HiveNodeFactory
from .history import CommandHistoryManager
from .inspector import HiveNodeInspector, BeeNodeInspector
from .models import model
from .node import FOLD_NODE_IMPORT_PATH, NodeTypes
from .utils import start_value_from_type, is_identifier, \
    camelcase_to_underscores


def _sanitise_variable(variable_name):
    variable_name = variable_name.lstrip('_')

    while not is_identifier(variable_name) or iskeyword(variable_name):
        variable_name = "{}_".format(variable_name)

    return variable_name


def _get_unique_name(existing_names, base_name):
    """Find unique value of base name which may have a number appended to the end

    :param existing_names: names currently in use
    :param base_name: base of name to use
    """
    # Return name without number if possible
    if base_name not in existing_names:
        return base_name

    i = 0
    while True:
        name = "{}_{}".format(base_name, i)
        if name not in existing_names:
            return name

        i += 1


class NodeConnectionError(Exception):
    pass


class NodeManager(object):

    def __init__(self, history, logger=None):
        if history is None:
            history = CommandHistoryManager()

        self.history = history

        self.bee_node_factory = BeeNodeFactory()
        self.hive_node_factory = HiveNodeFactory()

        self.hive_node_inspector = HiveNodeInspector()
        self.bee_node_inspector = BeeNodeInspector(self._find_attributes)

        self.docstring = ""
        self.nodes = {}

        self.on_node_created = None
        self.on_node_destroyed = None
        self.on_node_moved = None
        self.on_node_renamed = None

        self.on_connection_created = None
        self.on_connection_destroyed = None
        self.on_connection_reordered = None

        self.on_pin_folded = None
        self.on_pin_unfolded = None

        if logger is None:
            logger = logging.getLogger(repr(self))
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        self._logger = logger

    def _unique_name_from_import_path(self, import_path):
        obj_name = import_path.split(".")[-1]
        as_variable = camelcase_to_underscores(obj_name)

        as_variable = _sanitise_variable(as_variable)
        return _get_unique_name(self.nodes, as_variable)

    def _find_attributes(self):
        return {name: node for name, node in self.nodes.items() if node.import_path == "hive.attribute"}

    def _add_connection(self, connection):
        """Connect connection and push to history.

        :param connection: connection to connect
        """
        self.history.record_command(lambda: self._add_connection(connection),
                                    lambda: self.delete_connection(connection))

        connection.connect()

        # Ask GUI to perform connection
        if callable(self.on_connection_created):
            self.on_connection_created(connection)

        output_pin = connection.output_pin
        input_pin = connection.input_pin

        self._logger.info("Created connection between {}.{} and {}.{}"
                          .format(output_pin.node, output_pin.name, input_pin.node, input_pin.name))

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

        connection.delete()

        self.history.record_command(lambda: self.delete_connection(connection),
                                    lambda: self._add_connection(connection))

        self._logger.info("Deleted Connection: {}".format(connection))

    def delete_connections(self, connections):
        """Remove multiple connections from the model (as a composite operation)

        :param connections: Connection objects
        """
        with self.history.command_context("delete-connection-multiple"):
            for connection in connections:
                self.delete_connection(connection)

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

        self.history.record_command(lambda: self.reorder_connection(connection, index),
                                    lambda: self.reorder_connection(connection, old_index))

    def _add_node(self, node):
        """Add node to node dict and write to history.

        :param node: node to add
        """
        self.nodes[node.name] = node

        if callable(self.on_node_created):
            self.on_node_created(node)

        for pin in node.inputs.values():
            assert not pin.is_folded, (pin.name, pin.node)

        self.history.record_command(lambda: self._add_node(node), lambda: self.delete_node(node))

        # Ensure node restored to original place
        if callable(self.on_node_moved):
            self.on_node_moved(node, node.position)

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
            self._logger.error("Failed to inspect '{}'".format(import_path))
            raise

        try:
            node = self.hive_node_factory.new(name, import_path, params, param_info)

        except Exception:
            self._logger.error("Failed to instantiate '{}'".format(import_path))
            raise

        self._add_node(node)
        return node

    def delete_node(self, node):
        """Remove node and its connections from the model

        :param node: Node object
        """
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
            self.delete_connections(list(output_pin.connections))

        if callable(self.on_node_destroyed):
            self.on_node_destroyed(node)

        self.nodes.pop(node.name)

        self.history.record_command(lambda: self.delete_node(node), lambda: self._add_node(node))

    def delete_nodes(self, nodes):
        """Remove multiple nodes and their connections from the model (as a composite operation)

        :param nodes: Node objects
        """
        with self.history.command_context("delete-node-multiple"):
            for node in nodes:
                try:
                    self.delete_node(node)

                except KeyError:
                    continue

    def delete_all_nodes(self):
        nodes_to_delete = set(self.nodes.values())

        # Ignore folded nodes (handled)
        for node in self.nodes.values():
            for pin in node.inputs.values():
                if pin.is_folded:
                    target_connection = next(iter(pin.connections))
                    target_pin = target_connection.output_pin
                    folded_node = target_pin.node

                    nodes_to_delete.remove(folded_node)

        self.delete_nodes(nodes_to_delete)

    def rename_node(self, node, name, attempt_till_success=False):
        """Rename node with a new identifier

        :param node: Node object
        :param name: new name of node
        :param attempt_till_success: if name is not available, find a valid name based upon it
        """
        if name.startswith('_'):
            raise ValueError("Name must not start with '_'")

        if not is_identifier(name):
            raise ValueError("Name must be valid python identifier: {}".format(name))

        if iskeyword(name):
            raise ValueError("Name cannot be python keyword: {}".format(name))

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
        with node.make_writable():
            node.name = name

        if callable(self.on_node_renamed):
            self.on_node_renamed(node, name)

        self.history.record_command(lambda: self.rename_node(node, name),
                                    lambda: self.rename_node(node, old_name))

    def reposition_node(self, node, position):
        """Re-position node in the model

        :param node: Node object
        :param position: new x, y position
        """
        old_position = node.position

        with node.make_writable():
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
                self.reposition_node(other_node, new_position)

        if callable(self.on_node_moved):
            self.on_node_moved(node, position)

        self.history.record_command(lambda: self.reposition_node(node, position),
                                    lambda: self.reposition_node(node, old_position))

    def reposition_nodes(self, node_to_position):
        """Re-position multiple nodes in the model (as a composite operation)

        :param node_to_position: dictionary of node, position item pairs
        """
        with self.history.command_context("reposition-multiple"):
            for node, position in node_to_position.items():
                self.reposition_node(node, position)

    def fold_pin(self, pin):
        """Hide pin from node UI, as well as possible connected variable. If no variable, create, connect and hide.
        
        :param pin: IOPin object
        """
        assert pin.is_foldable

        # Create variable
        if not pin.connections:
            # TODO take start value from pin bee?
            params = dict(meta_args=dict(data_type=pin.data_type),
                          args=dict(start_value=start_value_from_type(pin.data_type)))

            # Create variable node, attempt to call it same as pin
            target_node = self.create_hive(FOLD_NODE_IMPORT_PATH, params)
            target_pin = next(iter(target_node.outputs.values()))

            self.rename_node(target_node, pin.name, attempt_till_success=True)
            self.create_connection(target_pin, pin)

            # TODO account for width of node and auto-arrange

        pin.is_folded = True

        if callable(self.on_pin_folded):
            self.on_pin_folded(pin)

        self.history.record_command(lambda: self.fold_pin(pin), lambda: self.unfold_pin(pin))

    def unfold_pin(self, pin):
        """Expose pin to node UI, as well as possible connected variable. If no variable, create, connect and show.

        :param pin: IOPin object
        """
        assert pin.is_folded
        assert pin.connections

        pin.is_folded = False

        if callable(self.on_pin_unfolded):
            self.on_pin_unfolded(pin)

        self.history.record_command(lambda: self.unfold_pin(pin), lambda: self.fold_pin(pin))

    def to_string(self):
        hivemap = self.to_hivemap()
        return str(hivemap)

    def load_string(self, data):
        # Validate type
        if not isinstance(data, str):
            raise TypeError("Loaded data should be a string type, not {}".format(type(data)))

        # Read hivemap
        hivemap = model.Hivemap(data)
        self.load_hivemap(hivemap)

    def to_hivemap(self):
        return self._export_to_hivemap(docstring=self.docstring)

    def load_hivemap(self, hivemap):
        with self.history.command_context("load"):
            # Clear nodes first
            self.delete_all_nodes()
            data = self._import_from_hivemap(hivemap)
            self.docstring = data['docstring']

    def cut(self, nodes):
        """Cut nodes to clipboard

        :param nodes: nodes to cut
        """
        with self.history.command_context("cut"):
            clipboard = self.copy(nodes)

            # Delete nodes
            self.delete_nodes(nodes)

        return clipboard

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

        return self._export_to_hivemap(with_folded_nodes)

    def paste(self, clipboard, position):
        """Paste nodes from clipboard

        :param position: position of target center of mass of nodes
        """
        with self.history.command_context("paste"):
            data = self._import_from_hivemap(clipboard)
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
                self.reposition_node(node, position)

    def _export_to_hivemap(self, nodes=None, docstring=""):
        if nodes is None:
            nodes = self.nodes.values()

        hivemap = model.Hivemap()
        hivemap.docstring = docstring

        for node in nodes:
            # Get node params
            params = node.params

            # Write to Bee
            meta_arg_array = dict_to_parameter_array(params.get('meta_args', {}))
            arg_array = dict_to_parameter_array(params.get('args', {}))

            folded_pins = [pin_name for pin_name, pin in node.inputs.items() if pin.is_folded]

            # Serialise HiveNode instance
            if node.node_type == NodeTypes.HIVE:
                cls_arg_array = dict_to_parameter_array(params.get('cls_args', {}))

                spyder_hive = model.HiveNode(identifier=node.name, import_path=node.import_path, position=node.position,
                                             meta_args=meta_arg_array, args=arg_array, cls_args=cls_arg_array,
                                             folded_pins=folded_pins)

                hivemap.hives.append(spyder_hive)

            # Serialise Bee instance
            elif node.node_type == NodeTypes.BEE:
                spyder_bee = model.BeeNode(identifier=node.name, import_path=node.import_path, position=node.position,
                                           meta_args=meta_arg_array, args=arg_array, folded_pins=folded_pins)
                hivemap.bees.append(spyder_bee)

        for node in nodes:
            node_name = node.name

            for pin_name, pin in node.outputs.items():
                for connection in pin.connections:
                    target_pin = connection.input_pin
                    target_node = target_pin.node

                    # Omit connections that aren't in the copied nodes
                    if target_node not in nodes:
                        continue

                    is_trigger = connection.is_trigger
                    spyder_connection = model.Connection(node_name, pin_name, target_node.name, target_pin.name,
                                                         is_trigger)
                    hivemap.connections.append(spyder_connection)

        return hivemap

    def _import_from_hivemap(self, hivemap):
        # Create nodes
        # Mapping from original ID to new ID
        id_to_node_name = {}
        node_to_spyder_hive_node = {}
        node_to_spyder_node = {}

        created_nodes = {}

        # Load IO bees
        for spyder_bee in hivemap.bees:
            import_path = spyder_bee.import_path

            meta_args = parameter_array_to_dict(spyder_bee.meta_args)
            args = parameter_array_to_dict(spyder_bee.args)

            params = {"meta_args": meta_args, "args": args}

            try:
                node = self.create_bee(import_path, params)

            except Exception as err:
                self._logger.exception("Unable to create node {}".format(spyder_bee.identifier))
                continue

            node_to_spyder_node[node] = spyder_bee

        # Load hives
        for spyder_hive in hivemap.hives:
            import_path = spyder_hive.import_path

            meta_args = parameter_array_to_dict(spyder_hive.meta_args)
            args = parameter_array_to_dict(spyder_hive.args)
            cls_args = parameter_array_to_dict(spyder_hive.cls_args)

            params = {"meta_args": meta_args, "args": args, "cls_args": cls_args}

            try:
                node = self.create_hive(import_path, params)

            except Exception as err:
                self._logger.exception("Unable to create node {}".format(spyder_hive.identifier))
                continue

            node_to_spyder_node[node] = spyder_hive

            # Specific mapping for Spyder HiveNodes only.
            node_to_spyder_hive_node[node] = spyder_hive

        # Attempt to set common data between IO bees and Hives
        for node, spyder_node in node_to_spyder_node.items():
            # Try to use original name, otherwise make unique
            self.rename_node(node, spyder_node.identifier, attempt_till_success=True)

            # Set original position
            self.reposition_node(node, (spyder_node.position.x, spyder_node.position.y))

            # Map original copied ID to new allocated ID
            node_name = node.name
            id_to_node_name[spyder_node.identifier] = node_name
            created_nodes[node_name] = node

        # Recreate connections
        for connection in hivemap.connections:
            try:
                from_id = id_to_node_name[connection.from_node]
                to_id = id_to_node_name[connection.to_node]

            except KeyError:
                self._logger.error("Unable to find all nodes in connection: {}, {}".format(connection.from_node, connection.to_node))
                continue

            from_node = created_nodes[from_id]
            to_node = created_nodes[to_id]

            try:
                from_pin = from_node.outputs[connection.output_name]
                to_pin = to_node.inputs[connection.input_name]

            except KeyError:
                self._logger.error("Unable to find all node pins in connection: {}.{}, {}.{}"
                                   .format(connection.from_node, connection.output_name, connection.to_node, connection.input_name))
                continue

            try:
                self.create_connection(from_pin, to_pin)

            except Exception:
                self._logger.exception("Unable to create connection between {}.{}, {}.{}"
                                       .format(connection.from_node, connection.output_name,
                                               connection.to_node, connection.input_name))

        # Fold folded pins
        for node, spyder_node in node_to_spyder_node.items():

            for pin_name in spyder_node.folded_pins:
                try:
                    pin = node.inputs[pin_name]

                except KeyError:
                    self._logger.error("Couldn't find pin {}.{} to fold".format(node.name, pin_name))
                    continue

                self.fold_pin(pin)

        return dict(nodes=created_nodes, docstring=hivemap.docstring)
