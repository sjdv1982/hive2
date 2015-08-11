from .hive_node import HiveNode
from .models import model
from .utils import import_from_path, eval_value


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

    def create_connection(self, output, input):
        output.connect(input)
        input.connect(output)

        self.gui_node_manager.create_connection(output, input)
        print("Create connection", output.name, output.node, input.name, input.node)

    def delete_connection(self, output, input):
        self.gui_node_manager.delete_connection(output, input)
        print("Delete Connection", output, input)
        output.disconnect(input)
        input.disconnect(output)

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
        self.nodes[name] = node

        self.gui_node_manager.create_node(node)

        return node

    def delete_node(self, node):
        # Remove connections
        for input in node.inputs.values():
            for output in input.targets.copy():
                self.delete_connection(output, input)

        for output in node.outputs.values():
            for input in output.targets.copy():
                self.delete_connection(output, input)

        self.gui_node_manager.delete_node(node)
        self.nodes.pop(node.name)

    def rename_node(self, node, name):
        if self.nodes.get(name, node) is not node:
            raise ValueError("Can't rename {} to {}".format(node, name))

        # Change key
        self.nodes.pop(node.name)
        self.nodes[name] = node

        # Update name
        node.name = name

        self.gui_node_manager.rename_node(node, name)

    def set_position(self, node, position):
        node.position = position

        self.gui_node_manager.set_position(node, position)

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
            self.set_position(node, position)

    def _export(self, nodes):
        hivemap = model.Hivemap()

        node_names = set()

        for node in nodes:
            # TODO, if bee is not hive
            args = [model.BeeInstanceParameter(name, info['data_type'], info['value'])
                    for name, info in node.info['args'].items()]

            spyder_bee = model.Bee(node.name, node.hive_path, args, node.position)
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
        node_id_mapping = {}
        nodes = set()

        for bee in hivemap.bees:
            import_path = bee.import_path

            params = {p.identifier: eval_value(p.value, p.data_type) for p in bee.args}

            try:
                node = self.create_node(import_path, params)

            except (ValueError, RuntimeError) as err:
                print("Unable to create node {}: {}".format(bee.identifier, err))
                continue

            try:
                self.rename_node(node, bee.identifier)

            except ValueError:
                print("Failed to rename")
                pass

            self.set_position(node, (bee.position.x, bee.position.y))

            # Map original copied ID to new allocated ID
            node_id_mapping[bee.identifier] = node.name

            nodes.add(node)

        self.on_pasted_pre_connect(nodes)

        for connection in hivemap.connections:
            try:
                from_id = node_id_mapping[connection.from_bee]
                to_id = node_id_mapping[connection.to_bee]

            except KeyError:
                print("Unable to create connection {}, {}".format(connection.from_bee,
                                                                  connection.to_bee))
                continue

            from_node = self.nodes[from_id]
            to_node = self.nodes[to_id]

            from_pin = from_node.outputs[connection.output_name]
            to_pin = to_node.inputs[connection.input_name]

            self.create_connection(from_pin, to_pin)

        return nodes