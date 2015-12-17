from .types import register as register_types
from .blend_manager import register as register_blend_manager
from .node_menu_manager import register as register_node_menu
from .gui_node_manager import register as register_node_manager
from .socket_manager import register as register_socket
from .node_categories import register as register_node_categories


def register():
    register_types()
    register_socket()
    register_node_categories()
    register_node_menu()
    register_node_manager()
    register_blend_manager()


def unregister():
    pass