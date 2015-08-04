from hive.tuple_type import types_match
from .hive_node import HiveNode
from .clipboard import Clipboard
from .utils import import_from_path


class NodeManager:

    def __init__(self, gui_node_manager):
        self.nodes = {}
        self.clipboard = Clipboard(self)
        self.gui_node_manager = gui_node_manager

        self._available_node_id = 0

    def get_unique_node_id(self):
        self._available_node_id += 1
        return self._available_node_id

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

        unique_id = self.get_unique_node_id()

        hive_cls = import_from_path(import_path)
        hive = hive_cls(**params)

        node = HiveNode(hive, import_path, unique_id=unique_id)
        self.nodes[unique_id] = node

        self.gui_node_manager.create_node(node)

        return node

    def delete_node(self, node):
        print("NM: DELETE ", node)
        # Remove connections
        for input in node.inputs.values():
            for output in input.targets.copy():
                self.delete_connection(output, input)

        for output in node.outputs.values():
            for input in output.targets.copy():
                self.delete_connection(output, input)

        self.gui_node_manager.delete_node(node)
        self.nodes.pop(node.unique_id)

    def rename_node(self, node, name):
        node.name = name
        self.gui_node_manager.rename_node(node, name)

    def set_position(self, node, position):
        node.position = position
        self.gui_node_manager.set_position(node, position)

    def on_pasted_pre_connect(self, nodes):
        self.gui_node_manager.on_pasted_pre_connect(nodes)

    def export(self):
        pass

    def load(self, data):
        pass