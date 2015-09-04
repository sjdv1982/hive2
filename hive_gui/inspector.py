from .utils import import_from_path, get_builder_class_args


class InspectorOption:
    """Configurable named field"""

    class NoValue:
        """Unique object used to indicate no value"""
        pass

    def __init__(self, name, data_type=None, default=NoValue, options=None):
        self.name = name
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

    def inspect_antenna(self):
        return no_inspector()

    def inspect_output(self):
        return no_inspector()

    def inspect_entry(self):
        return no_inspector()

    def inspect_hook(self):
        return no_inspector()

    def inspect_modifier(self):
        yield ("args", [InspectorOption("code", "str", "")])

    def inspect_triggerfunc(self):
        return no_inspector()

    def inspect_attribute(self):
        meta_args = yield ("meta_args", [InspectorOption("data_type", "tuple", ("int",))])
        data_type = meta_args['data_type'][0] if meta_args['data_type'] else None

        yield ("args", [InspectorOption("export", "bool", False), InspectorOption("start_value", data_type)])

    def inspect_pull_in(self):
        attributes = {name: node for name, node in self._node_manager.nodes.items()
                      if node.import_path == "hive.attribute"}

        meta_args = yield ("meta_args", [InspectorOption("attribute_name", "str", options=attributes.keys())])

        attribute_name = meta_args['attribute_name']
        attribute_node = attributes[attribute_name]

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

    def _scrape_wrapper(self, wrapper):
        """Scrape parameters from a HiveArgs wrapper

        :param wrapper: HiveArgs wrapper instance
        """
        wrapper_options = []

        for arg_name in wrapper:
            param = getattr(wrapper, arg_name)
            data_type = param.data_type[0] if param.data_type else None
            options = param.options

            # If default is defined
            default = param.start_value
            if default is param.NoValue:
                default = InspectorOption.NoValue

            wrapper_options.append(InspectorOption(arg_name, data_type, default, options))

        return wrapper_options

    def _inspect_generator(self, import_path):
        # Import and prepare hive
        hive_cls = import_from_path(import_path)

        # Prepare args wrapper
        hive_cls._hive_build_meta_args_wrapper()

        meta_args_wrapper = hive_cls._hive_meta_args
        if meta_args_wrapper:
            meta_args = yield ("meta_args", self._scrape_wrapper(meta_args_wrapper))
            _, _, hive_object_cls = hive_cls._hive_get_hive_object_cls((), meta_args)

        else:
            hive_object_cls = hive_cls._hive_build(())

        args_wrapper = hive_object_cls._hive_args
        if args_wrapper:
            yield ("args", self._scrape_wrapper(args_wrapper))

        builder_args = get_builder_class_args(hive_cls)
        if builder_args:
            options = [InspectorOption(name=name, default=data['default'])
                       for name, data in builder_args.items()]
            yield ("cls_args", options)