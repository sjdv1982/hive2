from nodeitems_utils import NodeItem

from .types import HiveNodeCategory


node_categories = [
    HiveNodeCategory("BEES", "Bees", items=[
        NodeItem("CustomNodeType"),
        ]),
    HiveNodeCategory("HIVES", "Hives", items=[
        ]),
    ]


def register():
    pass#register_node_categories("CUSTOM_NODES", node_categories)


def unregister():
    pass#unregister_node_categories("CUSTOM_NODES")