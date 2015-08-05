import spyder

from .hive_node import HiveNode
from .models import model
from .utils import import_from_path, eval_value


class Clipboard:

    def __init__(self, node_manager):
        self._data = None
        self._node_manager = node_manager

    def export(self, nodes):
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

        return str(hivemap)

    def load(self, data):
        if data is None:
            return []

        # Create nodes
        # Mapping from original ID to new ID
        node_id_mapping = {}
        nodes = set()

        if not isinstance(data, str):
            raise TypeError("Loaded data should be a string type, not {}".format(type(data)))

        hivemap = model.Hivemap(data)

        for bee in hivemap.bees:
            import_path = bee.import_path

            params = {p.identifier: eval_value(p.value, p.data_type) for p in bee.args}

            node = self._node_manager.create_node(import_path, params)

            try:
                print("PRENAME", node, bee.identifier)
                self._node_manager.rename_node(node, bee.identifier)

            except ValueError:
                print("Failed to rename")
                pass

            self._node_manager.set_position(node, (bee.position.x, bee.position.y))

            # Map original copied ID to new allocated ID
            node_id_mapping[bee.identifier] = node.name

            nodes.add(node)

        self._node_manager.on_pasted_pre_connect(nodes)

        for connection in hivemap.connections:
            from_id = node_id_mapping[connection.from_bee]
            to_id = node_id_mapping[connection.to_bee]

            from_node = self._node_manager.nodes[from_id]
            to_node = self._node_manager.nodes[to_id]

            from_pin = from_node.outputs[connection.output_name]
            to_pin = to_node.inputs[connection.input_name]

            self._node_manager.create_connection(from_pin, to_pin)

        return nodes

    def copy(self, nodes):
        self._data = self.export(nodes)

    def paste(self, position):
        nodes = self.load(self._data)

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
            self._node_manager.set_position(node, position)
