from bpy import app, data, types, props


from .text_area import BlenderTextAreaManager
from .types import HiveNodeTree
from .gui_node_manager import BlenderGUINodeManager
from .node_menu_manager import node_menu_manager, HiveNodeMenu

from ..node_manager import NodeManager

from ..finder import get_hives, recurse
hives = get_hives()

recurse("test.sca", hives)


class BlendManager:

    def __init__(self):
        self.text_area_manager = BlenderTextAreaManager()

        self._gui_node_managers = {}

        root_menu = node_menu_manager.create_menu("Hives")
        self.init_node_menu(hives, root_menu)

        # TODO fix deleting node trees

    def init_node_menu(self, hive_dict, menu):
        if isinstance(hive_dict, (list, set)):
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

    def get_gui_manager_for_node_tree(self, node_tree):
        return self._gui_node_managers[node_tree.unique_id]

    def get_gui_manager_for_node(self, gui_node):
        """Find the node tree interface for a given blender node"""
        for unique_id, interface in self._gui_node_managers.items():
            node_tree = interface.node_tree

            for node in node_tree.nodes.values():
                if gui_node.name == node.name:
                    return interface

        raise KeyError("Node not found: {}".format(gui_node))

    def reload_node_tree_from_source(self, node_tree):
        gui_manager = self.get_gui_manager_for_node_tree(node_tree)

        # Load text block
        resource_path = "{}.hivemap".format(node_tree.name)

        try:
            text_block = data.texts[resource_path]

        except KeyError:
            pass

        else:
            gui_manager.node_manager.load(text_block.as_string())

    def on_loaded(self):
        self._gui_node_managers.clear()

    def pre_saved(self):
        for unique_id, gui_manager in self._gui_node_managers.items():
            node_tree = gui_manager.node_tree

            node_manager = gui_manager.node_manager

            text_block_name = "{}.hivemap".format(node_tree.name)
            text_block = data.texts[text_block_name]

            text_block.from_string(node_manager.export())

        print("Saved texts")

    def sychronise_node_trees(self):
        text_block_paths = {t.name for t in data.texts if t.name.endswith("hivemap")}

        for node_tree in data.node_groups:
            if not node_tree.users:
                continue

            if not isinstance(node_tree, HiveNodeTree):
                continue

            resource_path = "{}.hivemap".format(node_tree.name)

            # Find node managers
            try:
                gui_node_manager = self.get_gui_manager_for_node_tree(node_tree)
                node_manager = gui_node_manager.node_manager

            except KeyError:
                # Assign unique ID
                unique_id = node_tree.unique_id = repr(node_tree.as_pointer())

                gui_node_manager = BlenderGUINodeManager(self, node_tree)
                node_manager = NodeManager(gui_node_manager)

                gui_node_manager.node_manager = node_manager
                self._gui_node_managers[unique_id] = gui_node_manager

                self.reload_node_tree_from_source(node_tree)

            if resource_path not in text_block_paths:
                if node_tree.previous_name:
                    previous_resource_path = "{}.hivemap".format(node_tree.previous_name)

                    # Migrate original text block
                    if previous_resource_path in text_block_paths:
                        text_block = data.texts[previous_resource_path]
                        text_block.name = resource_path

                        print("Migrating text block from {} to {}".format(previous_resource_path, resource_path))

                    # Couldn't migrate, create
                    else:
                        text_block = data.texts.new(resource_path)
                        text_block.from_string(node_manager.export())

                        print("Unexpected: Create text block for {}".format(resource_path))

                # Couldn't find original text block
                else:
                    text_block = data.texts.new(resource_path)
                    text_block.from_string(node_manager.export())

                    print("Create text block for {}".format(resource_path))

            gui_node_manager.update()

        # Add new
        for text_block_name in text_block_paths:
            hive_map_name = text_block_name[:-len(".hivemap")]

            # Node tree doesn't exist
            if hive_map_name not in data.node_groups:
                # Delete text
                text_block = data.texts[text_block_name]
                data.texts.remove(text_block)

                print("Deleting text block: no node tree exists for {}".format(text_block_name))

    def update(self, scene):
        self.sychronise_node_trees()
        self.text_area_manager.update()


blend_manager = BlendManager()


@app.handlers.persistent
def post_update(scene):
    try:
        blend_manager.update(scene)

    except Exception as err:
        unregister()
        raise


@app.handlers.persistent
def post_load(dummy):
    blend_manager.on_loaded()


@app.handlers.persistent
def save_pre(dummy):
    blend_manager.pre_saved()


def register():
    app.handlers.scene_update_post.append(post_update)
    app.handlers.load_post.append(post_load)
    app.handlers.save_pre.append(save_pre)

    types.Scene.use_hive = props.BoolProperty(default=False)


def unregister():
    del types.Scene.use_hive

    app.handlers.save_pre.remove(save_pre)
    app.handlers.load_post.remove(post_load)
    app.handlers.scene_update_post.remove(post_update)