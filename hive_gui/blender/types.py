from bpy import types, utils, props, ops
from nodeitems_utils import NodeCategory

from .text_area import BlenderTextArea

from ..utils import import_from_path,

blend_manager = None

LOCATION_DIVISOR = 1
INVALID_NODE_NAME = "<invalid>"
INVALID_NODE_ID = INVALID_NODE_TREE_ID = "<none>"


class HiveNodeTree(types.NodeTree):
    bl_idname = 'HiveNodeTree'
    bl_label = 'Custom Node Tree'
    bl_icon = 'GAME'

    previous_name = props.StringProperty()
    unique_id = props.StringProperty(INVALID_NODE_TREE_ID)


class HiveNodeCategory(NodeCategory):

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'HiveNodeTree'


class BlenderHiveNode(types.Node):
    bl_idname = "HiveNode"
    bl_label = bl_idname

    unique_id = props.StringProperty(INVALID_NODE_ID)

    def init(self, context):
        pass

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'HiveNodeTree'

    @property
    def gui_node_manager(self):
        return blend_manager.get_gui_manager_for_node_tree(self.id_data)

    def copy(self, node):
        self.gui_node_manager.gui_on_copied(node, self)

    def free(self):
        self.gui_node_manager.gui_on_freed(self)

    def draw_buttons(self, context, layout):
        parameters = self.gui_node_manager.gui_get_parameter_values(self)

        for name, data in parameters.items():
            value = data['value']

            row = layout.row(align=True)
            row.label("{}:".format(name))

            row.label(repr(value))

    def draw_buttons_ext(self, context, layout):
        pass

    def update(self):
        self.gui_node_manager.gui_on_updated(self)


# Custom socket type
class BlenderHiveSocket(types.NodeSocket):
    default_colour = (1.0, 0.4, 0.216, 0.5)

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return self.node.gui_node_manager.gui_get_socket_colour(self)


enum_data_types = [("str", "str", "String"),
                   ("bool", "bool", "Bool"), ("int", "int", "Int"),
                   ("float", "float", "Float")]


class ParameterGroup(types.PropertyGroup):
    name = props.StringProperty(name="Name")
    data_type = props.EnumProperty(items=enum_data_types)

    value_str = props.StringProperty()
    value_int = props.IntProperty()
    value_bool = props.BoolProperty()
    value_float = props.FloatProperty()

    @property
    def value(self):
        return getattr(self, "value_{}".format(self.data_type))

    @value.setter
    def value(self, value):
        setattr(self, "value_{}".format(self.data_type), value)


utils.register_class(ParameterGroup)


class ArgumentGroup(types.PropertyGroup):
    name = props.StringProperty(name="Name")
    value_repr = props.StringProperty()


utils.register_class(ArgumentGroup)


class HIVE_UL_parameters(types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        data_type = item.data_type

        layout.label(text=item.name.replace("_", " ").title())
        prop_row = layout.row()
        prop_row.prop(item, "value_{}".format(data_type), text="")


class HIVE_UL_arguments(types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.label(text=item.name.replace("_", " ").title())

        prop_row = layout.row()
        prop_row.prop(item, "value_repr", text="")


class NODE_OT_ConfigHiveNode(types.Operator):
    bl_idname = "hive.config_and_add_node"
    bl_label = "Configure Hive Node"

    import_path = props.StringProperty(name="Import path")

    arguments_index = props.IntProperty()
    arguments = props.CollectionProperty(type=ArgumentGroup)

    parameters_index = props.IntProperty()
    parameters = props.CollectionProperty(type=ParameterGroup)

    def draw(self, context):
        layout = self.layout
        layout.label("Parameters")
        layout.template_list("HIVE_UL_parameters", "", self, "parameters", self, "parameters_index")

        layout.label("Class Arguments")
        layout.template_list("HIVE_UL_arguments", "", self, "arguments", self, "arguments_index")

    def execute(self, context):
        params = {}

        for parameter in self.parameters:
            params[parameter.name] = parameter.value

        for argument in self.arguments:
            params[argument.name] = eval(argument.value_repr)

        add_hive_node(context, self.import_path, params)

        return {'FINISHED'}

    def invoke(self, context, event):
        hive_cls = import_from_path(self.import_path)
        init_info = get_pre_init_info(hive_cls)

        for name, info in init_info['parameters'].items():
            argument = self.parameters.add()
            argument.data_type = info['data_type'][0]
            argument.name = name
            argument.value = info['start_value']

        for name, info in init_info['cls_args'].items():
            argument = self.arguments.add()
            argument.name = name
            argument.value_repr = ''

        wm = context.window_manager
        return wm.invoke_props_dialog(self)


def add_hive_node(context, import_path, params=None):
    node_tree = context.space_data.edit_tree

    gui_node_manager = blend_manager.get_gui_manager_for_node_tree(node_tree)
    node_manager = gui_node_manager.node_manager

    node = node_manager.create_hive(import_path, params)
    gui_node = gui_node_manager.get_gui_node_from_node(node)

    # Select this node
    for gui_node_ in node_tree.nodes:
        gui_node_.select = False

    gui_node.select = True

    mouse_x, mouse_y = context.space_data.cursor_location
    position = mouse_x / LOCATION_DIVISOR, mouse_y / LOCATION_DIVISOR
    node_manager.set_node_position(node, position)

    # Invoke translation
    ops.transform.translate('INVOKE_DEFAULT')


class NODE_OT_AddHiveNode(types.Operator):
    bl_idname = "hive.add_node"
    bl_label = "Add Hive Node"

    import_path = props.StringProperty(default="dragonfly.std.Buffer", name="Import path")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        hive_cls = import_from_path(self.import_path)
        init_info = get_pre_init_info(hive_cls)

        if not (init_info['parameters'] or init_info['cls_args']):
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
        gui_node_manager = blend_manager.get_gui_manager_for_node_tree(node_tree)
        node_manager = gui_node_manager.node_manager

        # Get nodes
        node = gui_node_manager.gui_node_id_to_node[self.node_id]

        if event.type == 'MOUSEMOVE':
            mouse_x, mouse_y = context.space_data.cursor_location

            position = mouse_x / LOCATION_DIVISOR, mouse_y / LOCATION_DIVISOR
            node_manager.set_node_position(node, position)

        elif event.type in ('LEFTMOUSE', 'RETURN'):
            return {'FINISHED'}

        elif event.type == 'RIGHTMOUSE':
            node_manager.set_node_position(node, (0, 0))
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


class NODE_OT_ShowDocstring(types.Operator):
    bl_idname = "hive.edit_docstring"
    bl_label = "Edit Docstring"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        node_tree = context.space_data.edit_tree

        gui_node_manager = blend_manager.get_gui_manager_for_node_tree(node_tree)
        node_manager = gui_node_manager.node_manager

        set_docstring = lambda t: setattr(node_manager, 'docstring', t)
        get_docstring = lambda: node_manager.docstring

        text_area = BlenderTextArea(node_tree.name)

        text_area.on_write = set_docstring
        text_area.on_read = get_docstring
        text_area.write_on_edit = True

        blend_manager.text_area_manager.active_area = text_area

        return {'FINISHED'}


class HiveNodeTreeToolsMenu(types.Menu):
    """Tools menu for HIVE operations"""
    bl_label = "Hive Options"
    bl_idname = "NODE_MT_hive_menu"

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.operator("hive.synchronise_text_blocks", icon='FILE_REFRESH')
        col.operator("hive.edit_docstring", icon='INFO')


def draw_hive_menu(self, context):
    if isinstance(context.space_data.edit_tree, HiveNodeTree):
        self.layout.menu("NODE_MT_hive_menu")


_classes = (HiveNodeTree, BlenderHiveNode, BlenderHiveSocket, NODE_OT_AddHiveNode, NODE_OT_GrabHiveNode,
            HIVE_UL_arguments, HIVE_UL_parameters, NODE_OT_ConfigHiveNode, NODE_OT_SynchroniseTextBlocks,
            HiveNodeTreeToolsMenu, NODE_OT_ShowDocstring)


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