from .node import Node, NodeTypes, MimicFlags
from .utils import create_hive_object_instance, get_io_info, import_from_path, get_builder_class_args


class BeeNodeFactory:
    """Create bee nodes from import paths

    Bees cannot be inspected like Hives because they are the GUI primitives
    """

    def new(self, name, import_path, params):
        root, bee_name = import_path.split(".")
        assert root == "hive"

        builder = getattr(self, "build_{}".format(bee_name))
        return builder(name, import_path, params)

    def build_antenna(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)

        node.add_output("antenna", None, "any", max_connections=1, restricted_types=[("trigger",)],
                        mimic_flags=MimicFlags.COLOUR, is_proxy=True, count_proxies=True)

        return node

    def build_output(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)

        node.add_input("output", None, "any", max_connections=1, restricted_types=[("trigger",)],
                       mimic_flags=MimicFlags.COLOUR, is_proxy=True, count_proxies=True)

        return node

    def build_entry(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)

        node.add_output("output", ("trigger",), "push", max_connections=1, is_proxy=True, count_proxies=True)

        return node

    def build_hook(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)

        node.add_input("output", ("trigger",), "push", max_connections=1, is_proxy=True, count_proxies=True)

        return node

    def build_attribute(self, name, import_path, params):
        return Node(name, NodeTypes.BEE, import_path, params)

    def build_pull_in(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)
        data_type = params['meta_args']['data_type']

        node.add_input("value", data_type, "pull", restricted_types=[("trigger",)])
        node.add_input("trigger", ("trigger",), "push")

        node.add_output("pre_update", ("trigger",), "push", is_proxy=True)
        node.add_output("post_update", ("trigger",), "push")

        return node

    def build_pull_out(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)
        data_type = params['meta_args']['data_type']

        node.add_output("value", data_type, "pull", restricted_types=[("trigger",)])

        node.add_output("pre_output", ("trigger",), "push", is_proxy=True)
        node.add_output("post_output", ("trigger",), "push")

        return node

    def build_push_in(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)
        data_type = params['meta_args']['data_type']

        node.add_input("value", data_type, "push", restricted_types=[("trigger",)])

        node.add_output("pre_update", ("trigger",), "push", is_proxy=True)
        node.add_output("post_update", ("trigger",), "push")

        return node

    def build_push_out(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)
        data_type = params['meta_args']['data_type']

        node.add_output("value", data_type, "push", restricted_types=[("trigger",)])
        node.add_input("trigger", ("trigger",), "push")

        node.add_output("pre_output", ("trigger",), "push", is_proxy=True)
        node.add_output("post_output", ("trigger",), "push")

        return node

    def build_triggerfunc(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)

        node.add_output("trigger", ("trigger",), "push")
        node.add_output("pre_trigger", ("trigger",), "push", is_proxy=True)

        return node

    def build_modifier(self, name, import_path, params):
        node = Node(name, NodeTypes.BEE, import_path, params)

        node.add_input("trigger", ("trigger",), "push")

        return node


class HiveNodeFactory:
    """Create HIve nodes from import paths"""

    @staticmethod
    def new(name, import_path, params):
        hive_object = create_hive_object_instance(import_path, params)
        io_info = get_io_info(hive_object)

        # Warning later on, the args and cls_args of hive_object might not correspond to params
        # Altering the params dict from the UI is safe as it won't affect the pinout on the hiveobject, so these changes
        # Aren't mirrored to the args wrappers on this hive_object
        # Use the params dict instead of re-scraping the hive_object if reading these values

        node = Node(name, NodeTypes.HIVE, import_path, params)
        node.tooltip = hive_object.__doc__ or ""

        for pin_name, info in io_info['inputs'].items():
            node.add_input(pin_name, info['data_type'], info['mode'])

        for pin_name, info in io_info['outputs'].items():
            node.add_output(pin_name, info['data_type'], info['mode'])

        node.pin_order[:] = io_info['pin_order']

        return node


class HelperNodeFactory:
    """Helper nodes enable expression of non-bee constructs.

    They have no runtime presence themselves
    """
    _trigger_tooltip = \
"""
A trigger_{} helper enables nodes to hook into trigger and pretrigger events from the connected pin.
This helper has no build or runtime presence, only the connections to its trigger pins, implemented as triggers
"""

    def new(self, name, import_path, params):
        root, helper_name = import_path.split(".")
        builder = getattr(self, "build_{}".format(helper_name))

        return builder(name, import_path, params)
    #
    # def build_trigger_out(self, name, import_path, params):
    #     node = Node(name, NodeTypes.HELPER, import_path, params)
    #     node.tooltip = self._trigger_tooltip.format("out")
    #
    #     node.add_output("pretrigger", ("trigger",), "push", is_proxy=True)
    #     node.add_input("pin", data_type=None, mode="any", mimic_flags=MimicFlags.COLOUR | MimicFlags.SHAPE,
    #                    max_connections=1, is_proxy=True, count_proxies=True)
    #     node.add_output("trigger", ("trigger",), "push", is_proxy=True)
    #
    #     return node
    #
    # def build_trigger_in(self, name, import_path, params):
    #     node = Node(name, NodeTypes.HELPER, import_path, params)
    #     node.tooltip = self._trigger_tooltip.format("in")
    #
    #     node.add_output("pretrigger", ("trigger",), "push", is_proxy=True)
    #     node.add_output("pin", data_type=None, mode="any", mimic_flags=MimicFlags.COLOUR | MimicFlags.SHAPE,
    #                     max_connections=1, is_proxy=True, count_proxies=True)
    #     node.add_output("trigger", ("trigger",), "push", is_proxy=True)
    #
    #     return node