from bpy import types, utils, props, ops
from nodeitems_utils import NodeCategory

from ..sockets import colours, SocketTypes
from ..utils import import_from_path

blend_manager = None
LOCATION_DIVISOR = 100
INVALID_NODE_NAME = "<invalid>"


class HiveNodeTree(types.NodeTree):
    bl_idname = 'HiveNodeTree'
    bl_label = 'Custom Node Tree'
    bl_icon = 'NODETREE'

    previous_name = props.StringProperty()
    unique_id = props.IntProperty(-1)


class HiveNodeCategory(NodeCategory):

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'HiveNodeTree'


class BlenderHiveNode(types.Node):
    bl_idname = "HiveNode"
    bl_label = bl_idname

    unique_id = props.IntProperty(-1)

    def init(self, context):
        pass

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'HiveNodeTree'

    @property
    def gui_node_manager(self):
        return blend_manager.get_node_tree_manager_for_node(self)

    @property
    def node_tree(self):
        return self.gui_node_manager.node_tree

    def copy(self, node):
        self.gui_node_manager.gui_on_copied(node, self)

    def free(self):
        self.gui_node_manager.gui_on_freed(self)

    def draw_buttons(self, context, layout):
        pass

    def draw_buttons_ext(self, context, layout):
        pass

    def update(self):
        self.gui_node_manager.gui_on_updated(self)


# Custom socket type
class BlenderHiveSocket(types.NodeSocket):
    colour = (1.0, 0.4, 0.216, 0.5)

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return self.__class__.colour


enum_data_types = [("str", "str", "String"), ("bool", "bool", "Bool"), ("int", "int", "Int"),
                   ("float", "float", "Float")]


class ArgumentGroup(types.PropertyGroup):
    name = props.StringProperty(name="Name")
    data_type = props.EnumProperty(items=enum_data_types)

    value_str = props.StringProperty()
    value_int = props.IntProperty()
    value_bool = props.BoolProperty()
    value_float = props.FloatProperty()

    active = props.BoolProperty(name="Active")

    @property
    def value(self):
        return getattr(self, "value_{}".format(self.data_type))

    @value.setter
    def value(self, value):
        setattr(self, "value_{}".format(self.data_type), value)


utils.register_class(ArgumentGroup)


class HIVE_UL_arguments(types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        data_type = item.data_type

        layout.label(text=item.name)
        prop_row = layout.row()
        prop_row.prop(item, "value_{}".format(data_type), text="")

        layout.prop(item, "active", text="")


class NODE_OT_ConfigHiveNode(types.Operator):
    bl_idname = "hive.config_and_add_node"
    bl_label = "Configure Hive Node"

    import_path = props.StringProperty(name="Import path")

    arguments_index = props.IntProperty()
    arguments = props.CollectionProperty(type=ArgumentGroup)

    def draw(self, context):
        layout = self.layout
        layout.template_list("HIVE_UL_arguments", "", self, "arguments", self, "arguments_index")

    def execute(self, context):
        params = {}
        for argument in self.arguments:
            if not argument.active:
                continue

            params[argument.name] = argument.value

        add_hive_node(context, self.import_path, params)

        return {'FINISHED'}

    def invoke(self, context, event):
        hive_cls = import_from_path(self.import_path)
        hive_args = hive_cls._hive_args

        for name in hive_args:
            parameter = getattr(hive_args, name)
            base_type = parameter.data_type[0]

            argument = self.arguments.add()
            argument.data_type = base_type
            argument.name = name
            argument.value = parameter.start_value

        wm = context.window_manager
        return wm.invoke_props_dialog(self)


def add_hive_node(context, import_path, params=None):
    node_tree = context.space_data.edit_tree

    gui_node_manager = blend_manager.gui_node_managers[node_tree.unique_id]
    node_manager = gui_node_manager.node_manager

    node = node_manager.create_node(import_path, params)
    gui_node = gui_node_manager.get_gui_node_from_node(node)

    # Select this node
    for gui_node_ in node_tree.nodes:
        gui_node_.select = False

    gui_node.select = True

    mouse_x, mouse_y = context.space_data.cursor_location
    position = mouse_x / LOCATION_DIVISOR, mouse_y / LOCATION_DIVISOR
    node_manager.set_position(node, position)

    # Invoke translation
    ops.transform.translate('INVOKE_DEFAULT')


class NODE_OT_AddHiveNode(types.Operator):
    bl_idname = "hive.add_node"
    bl_label = "Add Hive Node"

    # TODO use list with custom prop type
    import_path = props.StringProperty(default="dragonfly.std.Buffer", name="Import path")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        hive_cls = import_from_path(self.import_path)

        # Build args if not built
        if hive_cls._hive_args is None:
            hive_cls._hive_build_args_wrapper()

        hive_args = hive_cls._hive_args

        if not hive_args:
            add_hive_node(context, self.import_path)

        else:
            ops.hive.config_and_add_node('INVOKE_DEFAULT', import_path=self.import_path)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NODE_OT_GrabHiveNode(types.Operator):
    bl_idname = "hive.grab_hive_node"
    bl_label = "Grab Hive Node"

    node_id = props.IntProperty()

    mouse_x = props.FloatProperty()
    mouse_y = props.FloatProperty()

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        node_tree = context.space_data.edit_tree
        gui_node_manager = blend_manager.gui_node_managers[node_tree]
        node_manager = gui_node_manager.node_manager

        # Get nodes
        node = gui_node_manager.gui_node_id_to_node[self.node_id]

        if event.type == 'MOUSEMOVE':
            mouse_x, mouse_y = context.space_data.cursor_location

            position = mouse_x / LOCATION_DIVISOR, mouse_y / LOCATION_DIVISOR
            node_manager.set_position(node, position)

        elif event.type in ('LEFTMOUSE', 'RETURN'):
            return {'FINISHED'}

        elif event.type == 'RIGHTMOUSE':
            node_manager.set_position(node, (0, 0))
            return {'FINISHED'}

        elif event.type == 'ESC':
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}


class NODE_OT_SynchroniseTextBlocks(types.Operator):
    bl_idname = "hive.synchronise_text_blocks"
    bl_label = "Reload From Text Block"

    node_id = props.IntProperty()

    mouse_x = props.FloatProperty()
    mouse_y = props.FloatProperty()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        blend_manager.reload_node_tree_from_source(node_tree)

        return {'FINISHED'}


class HiveNodeTreeToolsMenu(types.Menu):
    """Tools menu for HIVE operations"""
    bl_label = "Hive Options"
    bl_idname = "NODE_MT_hive_menu"

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.operator("hive.synchronise_text_blocks", icon="FILE_REFRESH")


def draw_hive_menu(self, context):
    self.layout.menu("NODE_MT_hive_menu")


_classes = (HiveNodeTree, BlenderHiveNode, BlenderHiveSocket, NODE_OT_AddHiveNode, NODE_OT_GrabHiveNode,
            HIVE_UL_arguments, NODE_OT_ConfigHiveNode, NODE_OT_SynchroniseTextBlocks, HiveNodeTreeToolsMenu)


def register():
    global blend_manager
    from .blend_manager import blend_manager

    for cls in _classes:
        utils.register_class(cls)

    types.NODE_HT_header.append(draw_hive_menu)


def unregister():
    for cls in _classes:
        utils.unregister_class(cls)

    types.NODE_HT_header.remove(draw_hive_menu)