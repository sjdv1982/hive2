from traceback import format_exc

from .connection import Connection, ConnectionType
from .factory import BeeNodeFactory, HiveNodeFactory
from .history import OperationHistory
from .inspector import HiveNodeInspector, BeeNodeInspector
from .models import model
from .node import NodeTypes
from .utils import start_value_from_type, dict_to_parameter_array, parameter_array_to_dict, is_identifier, \
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
        self.bee_node_inspector = BeeNodeInspector(self)

        self.docstring = ""
        self.nodes = {}
        self._clipboard = None

        # Hard coded paths for useful node types
        self.variable_import_path = "dragonfly.std.Variable"

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

    def create_connection(self, output_pin, input_pin):
        # Check pin isn't folded
        if input_pin.is_folded:
            raise NodeConnectionError("Cannot connect to a folded pin")

        # Check connection is permitted
        result = Connection.is_valid_between(output_pin, input_pin)

        if result == ConnectionType.INVALID:
            raise NodeConnectionError("Can't connect {} to {}".format(output_pin, input_pin))

        is_trigger = result == ConnectionType.TRIGGER
        connection = Connection(output_pin, input_pin, is_trigger=is_trigger)
        # Must call connection.connect()
        self._add_connection(connection)

    def _add_connection(self, connection):
        self.history.push_operation(self._add_connection, (connection,),
                                    self.delete_connection, (connection,))

        connection.connect()

        # Ask GUI to perform connection
        if callable(self.on_connection_created):
            self.on_connection_created(connection)

        output_pin = connection.output_pin
        input_pin = connection.input_pin
        print("Create connection", output_pin.name, output_pin.node, input_pin.name, input_pin.node)

    def delete_connection(self, connection):
        # Ask GUI to perform connection
        if callable(self.on_connection_destroyed):
            self.on_connection_destroyed(connection)

        print("Delete Connection", connection)

        connection.delete()

        self.history.push_operation(self.delete_connection, (connection,),
                                    self._add_connection, (connection,))

    def reorder_connection(self, connection, index):
        output_pin = connection.output_pin
        old_index = output_pin.connections.index(connection)

        output_pin.reorder_target(connection, index)

        # Ask GUI to reorder connection
        if callable(self.on_connection_reordered):
            self.on_connection_reordered(connection, index)

        self.history.push_operation(self.reorder_connection, (connection, index),
                                    self.reorder_connection, (connection, old_index))

    def create_hive(self, import_path, params=None):
        if params is None:
            params = {}

        name = self._unique_name_from_import_path(import_path)
        param_info = self.hive_node_inspector.inspect_configured(import_path, params)
        node = self.hive_node_factory.new(name, import_path, params, param_info)

        self._add_node(node)
        return node

    def create_bee(self, import_path, params=None):
        if params is None:
            params = {}

        name = self._unique_name_from_import_path(import_path)
        param_info = self.bee_node_inspector.inspect_configured(import_path, params)
        node = self.bee_node_factory.new(name, import_path, params, param_info)

        self._add_node(node)
        return node

    def _add_node(self, node):
        self.nodes[node.name] = node

        if callable(self.on_node_created):
            self.on_node_created(node)

        for pin in node.inputs.values():
            assert not pin.is_folded, (pin.name, pin.node)

        self.history.push_operation(self._add_node, (node,), self.delete_node, (node,))

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

    def can_fold_pin(self, pin):
        # Only hives support folding
        if pin.is_virtual:
            return False

        if pin.is_folded:
            return False

        if pin.io_type != "input":
            return False

        if pin.mode != "pull":
            return False

        if not pin.connections:
            return True

        if len(pin.connections) == 1:
            target_connection = next(iter(pin.connections))
            target_pin = target_connection.output_pin
            target_node = target_pin.node

            # If is not the correct type (variable)
            if target_node.import_path != self.variable_import_path:
                return False

            # If other pin is in use else where
            if len(target_pin.connections) == 1:
                return True

        return False

    def fold_pin(self, pin):
        assert self.can_fold_pin(pin)

        # Create variable
        if not pin.connections:
            # TODO take start value from pin bee?
            params = dict(meta_args=dict(data_type=pin.data_type),
                          args=dict(start_value=start_value_from_type(pin.data_type)))

            # Create variable node, attempt to call it same as pin
            target_node = self.create_hive(self.variable_import_path, params)
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

    def _paste_pre_connect(self, nodes):
        if callable(self.on_pasted_pre_connect):
            self.on_pasted_pre_connect(nodes)

    def export(self):
        hivemap = self.export_hivemap()
        return str(hivemap)

    def load(self, data):
        # Validate type
        if not isinstance(data, str):
            raise TypeError("Loaded data should be a string type, not {}".format(type(data)))

        # Read hivemap
        hivemap = model.Hivemap(data)
        self.load_hivemap(hivemap)

    def export_hivemap(self):
        hivemap = self._write(self.nodes.values())
        hivemap.docstring = self.docstring
        return hivemap

    def load_hivemap(self, hivemap):
        with self.history.composite_operation("load"):
            # Clear nodes first
            for node in list(self.nodes.values()):
                self.delete_node(node)

            self.docstring = hivemap.docstring
            self._read(hivemap)

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

        self._clipboard = self._write(with_folded_nodes)

    def paste(self, position):
        """Paste nodes from clipboard

        :param position: position of target center of mass of nodes
        """
        with self.history.composite_operation("paste"):
            nodes = self._read(self._clipboard)

            if nodes:
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

    @staticmethod
    def _write(nodes):
        hivemap = model.Hivemap()

        node_names = set()

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

            # Keep track of copied nodes
            node_names.add(node.name)

        for node in nodes:
            node_name = node.name

            for pin_name, pin in node.outputs.items():
                for connection in pin.connections:
                    target_pin = connection.input_pin
                    target_node_name = target_pin.node.name

                    # Omit connections that aren't in the copied nodes
                    if target_node_name not in node_names:
                        continue

                    is_trigger = connection.is_trigger
                    spyder_connection = model.Connection(node_name, pin_name, target_node_name, target_pin.name,
                                                         is_trigger)
                    hivemap.connections.append(spyder_connection)

        return hivemap

    def _read(self, hivemap):
        if hivemap is None:
            return []

        # Create nodes
        # Mapping from original ID to new ID
        nodes = set()
        id_to_node_name = {}
        node_to_spyder_hive_node = {}
        node_to_spyder_node = {}

        # Load IO bees
        for spyder_bee in hivemap.bees:
            import_path = spyder_bee.import_path

            meta_args = parameter_array_to_dict(spyder_bee.meta_args)
            args = parameter_array_to_dict(spyder_bee.args)

            params = {"meta_args": meta_args, "args": args}

            try:
                node = self.create_bee(import_path, params)

            except Exception as err:
                print("Unable to create node {}".format(spyder_bee.identifier))
                print(format_exc())
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
                print("Unable to create node {}".format(spyder_hive.identifier))
                print(format_exc())
                continue

            node_to_spyder_node[node] = spyder_hive

            # Specific mapping for Spyder HiveNodes only.
            node_to_spyder_hive_node[node] = spyder_hive

        # Attempt to set common data between IO bees and Hives
        for node, spyder_node in node_to_spyder_node.items():
            # Try to use original name
            try:
                self.set_node_name(node, spyder_node.identifier)

            except ValueError:
                print("Failed to use original name")
                pass

            # Set original position
            self.set_node_position(node, (spyder_node.position.x, spyder_node.position.y))

            # Map original copied ID to new allocated ID
            id_to_node_name[spyder_node.identifier] = node.name
            nodes.add(node)

        # Pre connectivity step (Blender hack)
        self._paste_pre_connect(nodes)

        # Recreate connections
        for connection in hivemap.connections:
            try:
                from_id = id_to_node_name[connection.from_node]
                to_id = id_to_node_name[connection.to_node]

            except KeyError:
                print("Unable to find all nodes in connection: {}, {}".format(connection.from_node, connection.to_node))
                continue

            from_node = self.nodes[from_id]
            to_node = self.nodes[to_id]

            try:
                from_pin = from_node.outputs[connection.output_name]
                to_pin = to_node.inputs[connection.input_name]

            except KeyError:
                print("Unable to find all node pins in connection: {}.{}, {}.{}".format(connection.from_node,
                                                                                        connection.output_name,
                                                                                        connection.to_node,
                                                                                        connection.input_name))
                continue

            self.create_connection(from_pin, to_pin)

        # Fold folded pins
        for node, spyder_node in node_to_spyder_node.items():
            for pin_name in spyder_node.folded_pins:
                pin = node.inputs[pin_name]
                self.fold_pin(pin)

        return nodes