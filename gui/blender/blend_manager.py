from bpy import app, data


from .types import HiveNodeTree
from .node_manager import BlenderGUINodeManager
from .node_menu_manager import node_menu_manager, HiveNodeMenu

from ..node_manager import NodeManager


hives = {"test": {"sca": {"actuators": ["Debug"], "sensors": ["Keyboard", "Always"], "controllers": ["AND", "NAND"]}}}


class BlendManager:

    def __init__(self):
        self.gui_node_managers = {}

        self.init_node_menu()

    # TODO, make this dynamic
    def init_node_menu(self, hive_dict=None, menu=None):
        if hive_dict is None:
            hive_dict = hives
            menu = node_menu_manager.create_menu("Hives")

        if isinstance(hive_dict, list):
            menu.children.append(hive_dict)
            return

        for name, child_dict in hive_dict.items():
            if menu.full_path:
                full_path = menu.full_path + "." + name

            else:
                full_path = name

            sub_menu = HiveNodeMenu(name, full_path)
            menu.children.append(sub_menu)

            self.init_node_menu(child_dict, sub_menu)

    def get_node_tree_manager_for_node(self, node):
        """Find the node tree interface for a given blender node"""
        for node_tree, interface in self.gui_node_managers.items():

            for node in node_tree.nodes.values():
                if node.unique_id == node.unique_id:
                    return interface

        raise KeyError("Node not found: {}".format(node))

    def on_loaded(self):
        self.gui_node_managers.clear()

    def update(self, scene):
        for node_tree in data.node_groups:
            if not node_tree.users:
                continue

            if not isinstance(node_tree, HiveNodeTree):
                continue

            try:
                gui_node_manager = self.gui_node_managers[node_tree]

            except KeyError:
                gui_node_manager = BlenderGUINodeManager(node_tree)
                node_manager = NodeManager(gui_node_manager)

                gui_node_manager.node_manager = node_manager
                self.gui_node_managers[node_tree] = gui_node_manager

            gui_node_manager.update()


blend_manager = BlendManager()


@app.handlers.persistent
def post_update(scene):
    try:
        blend_manager.update(scene)
    except Exception as err:
        unregister()
        print("STOP")
        raise


@app.handlers.persistent
def post_load(dummy):
    blend_manager.on_loaded()


def register():
    app.handlers.scene_update_post.append(post_update)
    app.handlers.load_post.append(post_load)


def unregister():
    app.handlers.load_post.remove(post_load)
    app.handlers.scene_update_post.remove(post_update)