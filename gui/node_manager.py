from hive.tuple_type import types_match
from .hive_node import HiveNode
from .clipboard import Clipboard
from .utils import import_from_path


def get_unique_name(existing_names, base_name):
    i = 0
    while True:
        name = "{}_{}".format(base_name, i)
        i += 1
        if name not in existing_names:
            return name


class NodeManager:

    def __init__(self, gui_node_manager):
        self.nodes = {}
        self.clipboard = Clipboard(self)
        self.gui_node_manager = gui_node_manager

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

        hive_cls = import_from_path(import_path)
        hive = hive_cls(**params)
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
        return self.clipboard.export(self.nodes.values())

    def load(self, hivemap):
        # Clear nodes first
        for node in self.nodes.values():
            self.delete_node(node)

        self.clipboard.load(hivemap)