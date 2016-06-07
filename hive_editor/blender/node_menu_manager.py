from bpy import utils, types


blend_manager = None


class HiveNodeMenu:

    def __init__(self, name, full_path=""):

        def draw(menu, context):
            layout = menu.layout
            layout.operator_context = 'INVOKE_DEFAULT'

            for child in self.children:
                if isinstance(child, self.__class__):
                    child.draw(layout)

                else:
                    if full_path:
                        child_path = full_path + "." + child

                    else:
                        child_path = child

                    operator = layout.operator("hive.add_node", text=child)
                    operator.reference_path = child_path

        # Create menu class
        menu_cls_dict = dict(draw=draw, bl_idname=repr(id(self)), bl_label=name)
        self._menu_cls = type(name, (types.Menu,), menu_cls_dict)
        utils.register_class(self._menu_cls)

        self.full_path = full_path
        self.name = name
        self.children = []

    def draw(self, layout):
        layout.menu(self._menu_cls.bl_idname)


class HiveNodeMenuManager:

    def __init__(self):
        self.menus = {}

    def create_menu(self, name, *args, **kwargs):
        menu = HiveNodeMenu(name, *args, **kwargs)
        self.menus[name] = menu
        return menu


node_menu_manager = HiveNodeMenuManager()


def draw_menu(self, context):
    # TODO only if menu is active
    layout = self.layout
    for name, menu in node_menu_manager.menus.items():
        menu.draw(layout)


def register():
    global blend_manager

    types.NODE_MT_add.append(draw_menu)


def unregister():
    types.NODE_MT_add.remove(draw_menu)