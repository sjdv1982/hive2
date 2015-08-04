from .types import BlenderHiveNode, LOCATION_DIVISOR
from .socket_manager import socket_class_manager

from ..sockets import get_colour, get_socket_type_for_mode

from ..gui_node_manager import IGUINodeManager

from contextlib import contextmanager
from collections import namedtuple
from logging import getLogger, INFO, basicConfig

from bpy import context
from functools import wraps

PendingOperation = namedtuple("PendingOperation", "type data")
default_operation = PendingOperation(None, None)


def wrapper(func, logger):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        logger.info("Entering {}".format(func.__name__))
        result = func(*args, **kwargs)
        logger.info("Exiting {}\n".format(func.__name__))
        return result
    return _wrapper


class BlenderGUINodeManager(IGUINodeManager):

    def __init__(self, node_tree):
        self.node_tree = node_tree
        self.node_manager = None

        self.node_to_gui_node = {}
        self.gui_node_id_to_node = {}

        self._internal_operations = [default_operation]
        self._updated_nodes = set()
        self._copied_nodes = set()
        self._pending_paste = False

        basicConfig(filename="D:/blendernodes.log", filemode="w")
        self._logger = getLogger("{}::{}".format(self.__class__.__name__, id(self)))
        self._logger.setLevel(INFO)

        for funcname in self.__class__.__dict__.keys():
            if funcname.startswith("__"):
                continue

            func = getattr(self, funcname)
            if callable(func):
                setattr(self, funcname, wrapper(func, self._logger))

    @property
    def internal_operation(self):
        if self._internal_operations:
            return self._internal_operations[-1]

        return None

    @contextmanager
    def internal_operation_from(self, type_, data=None):
        operation = PendingOperation(type_, data)

        self._internal_operations.append(operation)
        try:
            yield

        finally:
            self._internal_operations.pop()

    def create_connection(self, output, input):
        if self.internal_operation.type == "create_connection":
            self._logger.info("Ignoring create_connection request from node manager")
            return

        output_node = output.node
        input_node = input.node

        output_gui_node = self.node_to_gui_node[output_node]
        input_gui_node = self.node_to_gui_node[input_node]

        gui_output = output_gui_node.outputs[output.name]
        gui_input = input_gui_node.inputs[input.name]

        assert output_gui_node.name != input_gui_node.name

        self.node_tree.links.new(gui_input, gui_output)

    def delete_connection(self, output, input):
        if self.internal_operation.type == "delete_connection":
            self._logger.info("Ignoring delete_connection request from node manager")
            return

        print("PREDELETE", self.node_to_gui_node, input.node, output.node)
        output_gui_node = self.node_to_gui_node[output.node]
        input_gui_node = self.node_to_gui_node[input.node]

        output_socket = output_gui_node.outputs[output.name]
        input_socket = input_gui_node.inputs[input.name]

        # Find and remove link
        for link in self.node_tree.links:
            if link.from_socket == output_socket and link.to_socket == input_socket:
                self.node_tree.links.remove(link)
                return

    def create_node(self, node):
        gui_node = self.node_tree.nodes.new(BlenderHiveNode.bl_idname)
        gui_node.label = node.hive_class_name

        # Setup inputs
        for name, pin in node.inputs.items():
            socket_colour = get_colour(pin.data_type)
            socket_type = get_socket_type_for_mode(pin.mode)
            socket_cls = socket_class_manager.get_socket(socket_type, socket_colour)
            gui_node.inputs.new(socket_cls.bl_idname, name)

        # Setup outputs
        for name, pin in node.outputs.items():
            socket_colour = get_colour(pin.data_type)
            socket_type = get_socket_type_for_mode(pin.mode)
            socket_cls = socket_class_manager.get_socket(socket_type, socket_colour)
            gui_node.outputs.new(socket_cls.bl_idname, name)

        gui_node.unique_id = unique_id = node.unique_id

        self.node_to_gui_node[node] = gui_node
        self.gui_node_id_to_node[unique_id] = node

        self._logger.info("GUI created node: {}({})".format(node.name, node.unique_id))

    def delete_node(self, node):
        gui_node = self.node_to_gui_node.pop(node)
        self.gui_node_id_to_node.pop(gui_node.unique_id)
        print("FORGET_NODE", node)

        self._logger.info("GUI forgot node: {}({})".format(node.name, node.unique_id))

        if self.internal_operation.type != "node_freed":
            self._logger.info("GUI deleted node: {}({})".format(node.name, node.unique_id))
            self.node_tree.nodes.remove(gui_node)

    def rename_node(self, node, name):
        gui_node = self.node_to_gui_node[node]
        gui_node.label = name

    def on_pasted_pre_connect(self, nodes):
        """Called before pasted nodes are connected with one another

        Used to clear any Blender links
        """
        node_ids = {n.unique_id for n in nodes}

        to_remove = []
        for link in self.node_tree.links:
            self._logger.info("See link {}, {}".format(link.from_node, link.to_node))
            if link.from_node.unique_id in node_ids or link.to_node.unique_id in node_ids:
                to_remove.append(link)

        for link in to_remove:
            self.node_tree.links.remove(link)

    def set_position(self, node, position):
        if self.internal_operation.type == "set_position":
            return

        gui_node = self.node_to_gui_node[node]
        gui_node.location = position[0] * 100, position[1] * 100

    def gui_on_freed(self, gui_node):
        try:
            node = self.gui_node_id_to_node[gui_node.unique_id]
        except KeyError:
            return

        print("FREEING", node)

        with self.internal_operation_from("node_freed"):
            self.node_manager.delete_node(node)

    def gui_on_copied(self, old_gui_node, new_gui_node):
        self._copied_nodes.add((old_gui_node, new_gui_node))

    def gui_on_updated(self, gui_node):
        if self.internal_operation.type == "no_update":
            return

        # If is tracked; use id instead of reference due to crashing
        try:
            node = self.gui_node_id_to_node[gui_node.unique_id]

        except KeyError:
            return

        self._updated_nodes.add(node)

    def gui_post_copied(self, copied_gui_nodes):
        copied_nodes = set()

        pasting_from_clipboard = False

        for old_gui_node, new_gui_node in copied_gui_nodes:
            new_gui_node_name = new_gui_node.name

            # If a paste operation occurred
            if old_gui_node.name != new_gui_node_name:
                new_gui_node.unique_id = -1

                # Ensure no links are left (Blender nasty auto-connect)
                to_remove = []
                for link in self.node_tree.links:
                    if link.from_node.name == new_gui_node_name or link.to_node.name == new_gui_node_name:
                        to_remove.append(link)

                for link in to_remove:
                    self.node_tree.links.remove(link)

                # Remove node
                self.node_tree.nodes.remove(new_gui_node)

                # A new GUI node was added, indicating a paste should occur
                self._pending_paste = True

            # Add node to copied nodes set
            if not pasting_from_clipboard:
                try:
                    node = self.gui_node_id_to_node[old_gui_node.unique_id]

                except KeyError:
                    pasting_from_clipboard = True

                else:
                    copied_nodes.add(node)

        if not pasting_from_clipboard:
            print("COPY", copied_nodes)
            self.node_manager.clipboard.copy(copied_nodes)

        else:
            print("Pasting from clipboard, source nodes won't be there")

    def gui_post_pasted(self):
        position = context.space_data.cursor_location / LOCATION_DIVISOR
        self.node_manager.clipboard.paste(position)

    # TODO - expose unique name, not id
    def gui_post_updated(self, updated_nodes):
        node_to_gui_node = self.node_to_gui_node
        gui_node_id_to_node = self.gui_node_id_to_node

        for node in updated_nodes:
            try:
                gui_node = node_to_gui_node[node]

            except KeyError:
                continue

            # Find GUI missing pins
            for pin_name, from_pin in node.outputs.items():
                socket = gui_node.outputs[pin_name]

                found_gui_targets = set()

                # Traverse GUI connections
                for link in socket.links:
                    to_node = gui_node_id_to_node[link.to_node.unique_id]
                    to_pin = to_node.inputs[link.to_socket.name]

                    # Found something hive doesn't have
                    if to_pin not in from_pin.targets:
                        with self.internal_operation_from("create_connection"):
                            try:
                                self.node_manager.create_connection(from_pin, to_pin)
                                self._logger.info("Creating new HIVE connection from GUI: {}:{}, {}:{}"
                                                  .format(node.name, from_pin.name, to_pin.node.name, to_pin.name))
                                assert from_pin.node is not to_pin.node

                            except (TypeError, ValueError):
                                self.delete_connection(from_pin, to_pin)

                    # Keep track of defined GUI links from this node to connected nodes
                    found_gui_targets.add(to_pin)

                # Found targets that aren't in GUI, so are removed
                for to_pin in (from_pin.targets - found_gui_targets):
                    with self.internal_operation_from("delete_connection"):
                        self._logger.info("Deleting old GUI connection not in HIVE: {}:{}, {}:{}"
                                          .format(node.name, from_pin.name, to_pin.node.name, to_pin.name))
                        self.node_manager.delete_connection(from_pin, to_pin)

                self._logger.info("POST DELETE")

            gui_node_position = gui_node.location
            node_position = list(gui_node_position / LOCATION_DIVISOR)

            with self.internal_operation_from("set_position"):
                self.node_manager.set_position(node, node_position)

    def update(self):
        for node, gui_node in self.node_to_gui_node.items():
            if node.name != gui_node.label:
                self.node_manager.rename_node(node, gui_node.label)

        if self._updated_nodes:
            self.gui_post_updated(self._updated_nodes)
            self._updated_nodes.clear()

        if self._copied_nodes:
            self.gui_post_copied(self._copied_nodes)
            self._copied_nodes.clear()

        if self._pending_paste:
            self.gui_post_pasted()
            self._pending_paste = False


def register():
    pass


def unregister():
    pass