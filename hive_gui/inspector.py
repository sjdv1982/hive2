from collections import OrderedDict

from hive import validation_enabled_as
from .utils import import_from_path, get_builder_class_args


class InspectorOption:
    """Configurable named field"""

    class NoValue:
        """Unique object used to indicate no value"""
        pass

    def __init__(self, data_type=None, default=NoValue, options=None):
        self.data_type = data_type
        self.default = default
        self.options = options


def no_inspector():
    """Call to return no-op generator"""
    return
    yield


class BeeNodeInspector:

    def __init__(self, node_manager):
        self._node_manager = node_manager

    def inspect(self, import_path):
        """Inspect the UI attributes available for a bee with the given import path"""
        root, bee_name = import_path.split(".")
        assert root == "hive"

        inspector = getattr(self, "inspect_{}".format(bee_name))
        return inspector()

    def inspect_configured(self, import_path, params):
        inspector = self.inspect(import_path)
        param_info = {}

        # Find first stage values
        previous_values = None
        while True:
            try:
                stage_name, stage_options = inspector.send(previous_values)

            except StopIteration:
                break

            param_info[stage_name] = stage_options
            previous_values = params[stage_name]

        return param_info

    def inspect_antenna(self):
        return no_inspector()

    def inspect_output(self):
        return no_inspector()

    def inspect_entry(self):
        return no_inspector()

    def inspect_hook(self):
        return no_inspector()

    def inspect_modifier(self):
        args_options = OrderedDict()
        args_options["code"] = InspectorOption(("str", "code"), "")
        yield ("args", args_options)

    def inspect_triggerfunc(self):
        return no_inspector()

    def inspect_attribute(self):
        # Configure meta args
        meta_arg_options = OrderedDict()
        meta_arg_options["data_type"] = InspectorOption(("tuple",), ("int",))
        meta_args = yield ("meta_args", meta_arg_options)

        data_type = meta_args['data_type']

        # Configure ARGS
        arg_options = OrderedDict()
        arg_options["export"] = InspectorOption(("bool",), False)
        arg_options["start_value"] = InspectorOption(data_type)

        yield ("args", arg_options)

    def inspect_pull_in(self):
        attributes = {name: node for name, node in self._node_manager.nodes.items()
                      if node.import_path == "hive.attribute"}

        # Configure meta args
        meta_arg_options = OrderedDict()
        meta_arg_options["attribute_name"] = InspectorOption(("str",), options=set(attributes))
        meta_args = yield ("meta_args", meta_arg_options)

        attribute_name = meta_args['attribute_name']

        try:
            attribute_node = attributes[attribute_name]

        except KeyError:
            pass

        else:
            # TODO how can this better be supported so attributes can be renamed
            # Find bound attribute and save data type to meta_args
            meta_args['data_type'] = attribute_node.params['meta_args']['data_type']

    inspect_pull_out = inspect_pull_in
    inspect_push_out = inspect_pull_in
    inspect_push_in = inspect_pull_in


class HiveNodeInspector:

    def inspect(self, import_path):
        """Inspect the UI attribute available for a hive with the given import path

        :param import_path: import path of Hive class
        """
        return self._inspect_generator(import_path)

    def inspect_configured(self, import_path, params):
        inspector = self.inspect(import_path)
        param_info = {}

        # Find first stage values
        previous_values = None
        while True:
            try:
                stage_name, stage_options = inspector.send(previous_values)

            except StopIteration:
                break

            param_info[stage_name] = stage_options
            previous_values = params[stage_name]

        return param_info

    def _scrape_wrapper(self, wrapper):
        """Scrape parameters from a HiveArgs wrapper

        :param wrapper: HiveArgs wrapper instance
        """
        wrapper_options = OrderedDict()

        for arg_name in wrapper:
            param = getattr(wrapper, arg_name)
            data_type = param.data_type if param.data_type else ()
            options = param.options

            # If default is defined
            default = param.start_value
            if default is param.NoValue:
                option = InspectorOption(data_type, options=options)

            else:
                option = InspectorOption(data_type, default, options)

            wrapper_options[arg_name] = option

        return wrapper_options

    def _inspect_generator(self, import_path):
        with validation_enabled_as(False):
            # Import and prepare hive
            hive_cls = import_from_path(import_path)

            # Prepare args wrapper
            hive_cls._hive_build_meta_args_wrapper()

            meta_args_wrapper = hive_cls._hive_meta_args
            if meta_args_wrapper:
                meta_args = yield ("meta_args", self._scrape_wrapper(meta_args_wrapper))

                # Create HiveObject class
                _, _, hive_object_cls = hive_cls._hive_get_hive_object_cls((), meta_args)

            else:
                hive_object_cls = hive_cls._hive_build(())

            args_wrapper = hive_object_cls._hive_args
            if args_wrapper:
                yield ("args", self._scrape_wrapper(args_wrapper))

            builder_args = get_builder_class_args(hive_cls)
            if builder_args:
                # Convert options into InspectorOptions
                options = OrderedDict()
                for name, data in builder_args.items():
                    options[name] = InspectorOption(data["data_type"], data["default"], data["options"])

                yield ("cls_args", options)
