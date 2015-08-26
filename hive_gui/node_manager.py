from .hive_node import HiveNode
from .models import model
from .utils import import_from_path, eval_value
from contextlib import contextmanager


def get_unique_name(existing_names, base_name):
    i = 0
    while True:
        name = "{}_{}".format(base_name, i)
        i += 1
        if name not in existing_names:
            return name


class AtomicOperations:

    def __init__(self, limit=200):
        self._stack = []
        self._index = -1
        self._limit = limit

        self.guard = False

    @contextmanager
    def guarded(self):
        self.guard = True
        yield
        self.guard = False

    def undo(self):
        if self._index < 0:
            return

        last_operation = self._stack[self._index]
        op, args, reverse_op, reverse_args = last_operation

        with self.guarded():
            reverse_op(*reverse_args)

        self._index -= 1

    def redo(self):
        if self._index >= (len(self._stack) - 1):
            return

        self._index += 1

        operation = self._stack[self._index]
        op, args, reverse_op, reverse_args = operation

        with self.guarded():
            op(*args)

    def push_operation(self, op, args, reverse_op, reverse_args):
        if self.guard:
            return

        self._stack.append((op, args, reverse_op, reverse_args))

        # Limit length
        if len(self._stack) > self._limit:
            self._stack[:] = self._stack[-self._limit:]

        else:
            self._index += 1


class NodeManager:

    def __init__(self, gui_node_manager):
        self.docstring = ""
        self.gui_node_manager = gui_node_manager
        self.nodes = {}

        self._clipboard = None

        self.history = AtomicOperations()
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

        try:
            hive_cls = import_from_path(import_path)

        except (ImportError, AttributeError):
            raise ValueError("Invalid import path: {}".format(import_path))

        try:
            hive = hive_cls(**params)

        except Exception as err:
            raise RuntimeError("Unable to insantiate Hive cls {}: {}".format(hive_cls, err))

        name = get_unique_name(self.nodes, hive_cls.__name__)

        node = HiveNode(hive, import_path, name)

        self._add_node(node)

        return node

    def _add_node(self, node):
        print("ADD NODE",node)
        self.nodes[node.name] = node
        self.gui_node_manager.create_node(node)

        self.history.push_operation(self._add_node, (node,), self.delete_node, (node,))

    def delete_node(self, node):
        print("DELETE NODE")
        # Remove connections
        for input in node.inputs.values():
            for output in input.targets.copy():
                self.delete_connection(output, input)

        for output in node.outputs.values():
            for input in output.targets.copy():
                self.delete_connection(output, input)

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
            target_node = self.create_node(self.fold_node_path)
            target_pin = next(iter(target_node.outputs.values()))
            self.create_connection(target_pin, pin)

        pin.is_folded = True

        self.gui_node_manager.fold_pin(pin)
        self.history.push_operation(self.fold_pin, (pin,), self.unfold_pin, (pin,))

    def unfold_pin(self, pin):
        assert pin.is_folded
        assert pin.targets

        pin.is_folded = False

        self.gui_node_manager.unfold_pin(pin)
        self.history.push_operation(self.unfold_pin, (pin,), self.fold_pin, (pin,))

    def on_pasted_pre_connect(self, nodes):
        self.gui_node_manager.on_pasted_pre_connect(nodes)

    def export(self):
        hivemap = self._export(self.nodes.values())
        hivemap.docstring = self.docstring

        return str(hivemap)

    def load(self, data):
        # Clear nodes first
        for node in list(self.nodes.values()):
            self.delete_node(node)

        # Validate type
        if not isinstance(data, str):
            raise TypeError("Loaded data should be a string type, not {}".format(type(data)))

        # Read hivemap
        hivemap = model.Hivemap(data)
        self.docstring = hivemap.docstring

        self._load(hivemap)

    def copy(self, nodes):
        """Copy nodes to clipboard

        :param nodes: nodes to copy
        """
        self._clipboard = self._export(nodes)

    def paste(self, position):
        """Paste nodes from clipboard

        :param position: position of target center of mass of nodes
        """
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

        for node in nodes:
            # TODO, if bee is not hive
            args = [model.BeeInstanceParameter(name, info['data_type'], info['value'])
                    for name, info in node.post_init_info.items()]
            folded_pins = [pin_name for pin_name, pin in node.inputs.items() if pin.is_folded]

            spyder_bee = model.Bee(node.name, node.hive_path, args, node.position, folded_pins)
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

            params = {p.identifier: eval_value(p.value, p.data_type) for p in bee.args}

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