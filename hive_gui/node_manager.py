from .history import History
from .hive_node import HiveNode
from .models import model
from .utils import start_value_from_type, create_hive_object_instance, dict_to_parameter_array, parameter_array_to_dict



def get_unique_name(existing_names, base_name):
    i = 0
    while True:
        name = "{}_{}".format(base_name, i)
        i += 1
        if name not in existing_names:
            return name


class NodeManager:

    def __init__(self, gui_node_manager):
        self.docstring = ""
        self.gui_node_manager = gui_node_manager
        self.nodes = {}

        self._clipboard = None

        self.history = History()
        self.fold_node_path = "dragonfly.std.Variable"

    def create_connection(self, output, input):
        # Check pin isn't folded
        if input.is_folded:
            raise ValueError("Cannot connect to a folded pin")

        output.connect(input)
        input.connect(output)

        self.gui_node_manager.create_connection(output, input)
        self.history.push_operation(self.create_connection, (output, input), self.delete_connection, (output, input))

        print("Create connection", output.name, output.node, input.name, input.node)

    def delete_connection(self, output, input):
        self.gui_node_manager.delete_connection(output, input)
        print("Delete Connection", output, input)

        output.disconnect(input)
        input.disconnect(output)

        self.history.push_operation(self.delete_connection, (output, input), self.create_connection, (output, input))

    def create_node(self, import_path, params=None):
        if params is None:
            params = {}

        hive = create_hive_object_instance(import_path, params)

        # Get unique name from hive parent class name
        hive_class_name = hive._hive_parent_class.__name__
        name = get_unique_name(self.nodes, hive_class_name)

        node = HiveNode(hive, import_path, name, params)
        self._add_node(node)

        return node

    def _add_node(self, node):
        self.nodes[node.name] = node
        self.gui_node_manager.create_node(node)

        for pin in node.inputs.values():
            assert not pin.is_folded, (pin.name, pin.node)

        self.history.push_operation(self._add_node, (node,), self.delete_node, (node,))

    def delete_node(self, node):
        # Remove connections
        for input_pin in node.inputs.values():
            for output_pin in input_pin.targets.copy():

                # Handle folded nodes
                is_folded = input_pin.is_folded

                if is_folded:
                    self.unfold_pin(input_pin)

                self.delete_connection(output_pin, input_pin)

                # Delete folded nodes
                if is_folded:
                    self.delete_node(output_pin.node)

        for output_pin in node.outputs.values():
            for input_pin in output_pin.targets.copy():
                self.delete_connection(output_pin, input_pin)

        self.gui_node_manager.delete_node(node)
        self.nodes.pop(node.name)

        self.history.push_operation(self.delete_node, (node, ), self._add_node, (node,))

    def set_node_name(self, node, name):
        if self.nodes.get(name, node) is not node:
            raise ValueError("Can't rename {} to {}".format(node, name))

        # Change key
        old_name = node.name

        self.nodes.pop(old_name)
        self.nodes[name] = node

        # Update name
        node.name = name

        self.gui_node_manager.set_node_name(node, name)
        self.history.push_operation(self.set_node_name, (node, name), self.set_node_name, (node, old_name))

    def set_node_position(self, node, position):
        old_position = node.position
        node.position = position

        # Move folded nodes too
        dx = position[0] - old_position[0]
        dy = position[1] - old_position[1]

        for pin in node.inputs.values():
            if pin.is_folded:
                target_pin = next(iter(pin.targets))
                other_node = target_pin.node
                new_position = other_node.position[0] + dx, other_node.position[1] + dy
                self.set_node_position(other_node, new_position)

        self.gui_node_manager.set_node_position(node, position)

        self.history.push_operation(self.set_node_position, (node, position),
                                    self.set_node_position, (node, old_position))

    def can_fold_pin(self, pin):
        if pin.is_folded:
            return False

        if pin.io_type != "input":
            return False

        if pin.mode != "pull":
            return False

        if not pin.targets:
            return True

        if len(pin.targets) == 1:
            target_pin = next(iter(pin.targets))
            target_node = target_pin.node

            # If is not the correct type (variable)
            if target_node.hive_path != self.fold_node_path:
                return False

            # This pin is the only connected one
            if len(target_pin.targets) == 1:
                return True

        return False

    def fold_pin(self, pin):
        assert self.can_fold_pin(pin)

        # Create variable
        if not pin.targets:
            params = dict(meta_args=dict(data_type=pin.data_type),
                          args=dict(start_value=start_value_from_type(pin.data_type)))
            target_node = self.create_node(self.fold_node_path, params)
            target_pin = next(iter(target_node.outputs.values()))
            self.create_connection(target_pin, pin)

        pin.is_folded = True
        print("FOLDED", pin.name, pin.node)

        self.gui_node_manager.fold_pin(pin)
        self.history.push_operation(self.fold_pin, (pin,), self.unfold_pin, (pin,))

    def unfold_pin(self, pin):
        assert pin.is_folded
        assert pin.targets

        pin.is_folded = False
        print("UNFOLDED", pin.name, pin.node)

        self.gui_node_manager.unfold_pin(pin)
        self.history.push_operation(self.unfold_pin, (pin,), self.fold_pin, (pin,))

    def get_folded_value(self, pin):
        target_pin = next(iter(pin.targets))
        folded_node = target_pin.node

        return folded_node.params['args']['start_value']

    def set_folded_value(self, pin, value):
        target_pin = next(iter(pin.targets))
        folded_node = target_pin.node

        folded_node.params['args']['start_value'] = value

    def on_pasted_pre_connect(self, nodes):
        self.gui_node_manager.on_pasted_pre_connect(nodes)

    def export(self):
        hivemap = self._export(self.nodes.values())
        hivemap.docstring = self.docstring

        return str(hivemap)

    def load(self, data):
        with self.history.composite_operation("load"):
            # Clear nodes first
            for node in list(self.nodes.values()):
                self.delete_node(node)

            # Validate type
            if not isinstance(data, str):
                raise TypeError("Loaded data should be a string type, not {}".format(type(data)))

            # Read hivemap
            hive_map = model.Hivemap(data)
            self.docstring = hive_map.docstring

            self._load(hive_map)

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
                    target = next(iter(pin.targets)).node
                    with_folded_nodes.add(target)

        self._clipboard = self._export(with_folded_nodes)

    def paste(self, position):
        """Paste nodes from clipboard

        :param position: position of target center of mass of nodes
        """
        with self.history.composite_operation("paste"):
            nodes = self._load(self._clipboard)

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

    def _export(self, nodes):
        hivemap = model.Hivemap()

        node_names = set()

        # TODO, if bee is not hive
        for node in nodes:
            params = node.params

            # Write to Bee
            meta_arg_array = dict_to_parameter_array(params.get('meta_args', {}))
            arg_array = dict_to_parameter_array(params.get('args', {}))
            cls_arg_array = dict_to_parameter_array(params.get('cls_args', {}))

            folded_pins = [pin_name for pin_name, pin in node.inputs.items() if pin.is_folded]
            spyder_bee = model.Bee(node.name, node.hive_path, meta_arg_array, arg_array, cls_arg_array, node.position,
                                   folded_pins)

            hivemap.bees.append(spyder_bee)

            # Keep track of copied nodes
            node_names.add(node.name)

        for node in nodes:
            node_name = node.name

            for pin_name, pin in node.outputs.items():
                if not pin.targets:
                    continue

                pin_name = pin.name

                for target in pin.targets:
                    target_node_name = target.node.name

                    # Omit connections that aren't in the copied nodes
                    if target_node_name not in node_names:
                        continue

                    spyder_connection = model.BeeConnection(node_name, pin_name,
                                                            target_node_name, target.name)
                    hivemap.connections.append(spyder_connection)

        return hivemap

    def _load(self, hivemap):
        if hivemap is None:
            return []

        # Create nodes
        # Mapping from original ID to new ID
        nodes = set()
        nodes_to_bees = {}
        id_to_node_name = {}

        for bee in hivemap.bees:
            import_path = bee.import_path

            meta_args = parameter_array_to_dict(bee.meta_args)
            args = parameter_array_to_dict(bee.args)
            cls_args = parameter_array_to_dict(bee.cls_args)

            params = {"meta_args": meta_args, "args": args, "cls_args": cls_args}

            try:
                node = self.create_node(import_path, params)

            except (ValueError, RuntimeError) as err:
                print("Unable to create node {}: {}".format(bee.identifier, err))
                continue

            # Try to use original name
            try:
                self.set_node_name(node, bee.identifier)

            except ValueError:
                print("Failed to use original name")
                pass

            # Set original position
            self.set_node_position(node, (bee.position.x, bee.position.y))

            # Map original copied ID to new allocated ID
            id_to_node_name[bee.identifier] = node.name

            nodes.add(node)
            nodes_to_bees[node] = bee

        # Pre connectivity step (Blender hack)
        self.on_pasted_pre_connect(nodes)

        # Recreate connections
        for connection in hivemap.connections:
            try:
                from_id = id_to_node_name[connection.from_bee]
                to_id = id_to_node_name[connection.to_bee]

            except KeyError:
                print("Unable to create connection {}, {}".format(connection.from_bee,
                                                                  connection.to_bee))
                continue

            from_node = self.nodes[from_id]
            to_node = self.nodes[to_id]

            from_pin = from_node.outputs[connection.output_name]
            to_pin = to_node.inputs[connection.input_name]

            self.create_connection(from_pin, to_pin)

        # Fold folded pins
        for node, bee in nodes_to_bees.items():
            for pin_name in bee.folded_pins:
                pin = node.inputs[pin_name]
                self.fold_pin(pin)

        return nodes