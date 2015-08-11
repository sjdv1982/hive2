from bpy.utils import register_class

from .types import BlenderHiveSocket
from ..sockets import colours, SocketTypes


class SocketClassManager:
    """Find appropriate socket class for info"""
    
    def __init__(self):
        self._sockets = {}
    
    def register_socket(self, socket_type, socket_colour):
        blender_colour = (socket_colour[0]/255, socket_colour[1]/255, socket_colour[2]/255, 1.0)
        socket_cls = type("CustomSocket", (BlenderHiveSocket,), {'bl_idname': "SOCK{}".format(len(self._sockets)),
                                                                 'default_colour': blender_colour, 'socket_type': socket_type})
        register_class(socket_cls)
        # Save socket
        key = socket_type, socket_colour
        self._sockets[key] = socket_cls
    
    def get_socket(self, socket_type, socket_colour):
        key = socket_type, socket_colour
        return self._sockets[key]
    
    
socket_class_manager = SocketClassManager()


def register():
    for colour in colours:
        for socket_type in (SocketTypes.circle, SocketTypes.diamond, SocketTypes.square):
            socket_class_manager.register_socket(socket_type, colour)
