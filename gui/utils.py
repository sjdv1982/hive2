import ast

import hive

# IO bees
from hive.hook import Hook
from hive.entry import Entry
from hive.antenna import HiveAntenna
from hive.output import HiveOutput

from collections import OrderedDict
from inspect import getargspec
from itertools import chain
from os import path
from re import sub as re_sub
import sys

# Factories for types
type_factories = {
    "vector": lambda: (0.0, 0.0, 0.0),
    "colour": lambda: (0.0, 0.0, 0.0),
    "euler": lambda: (0.0, 0.0, 0.0),
    "str": str,
    "bool": bool,
    "int": int,
    "float": float,
    "tuple": tuple,
    "list": list,
    "dict": dict,
    "set": set,
}


def _get_type_name(value):
    """Helper function

    Used to write the type name to a hive BeeInstanceParameter
    """
    return value.__class__.__name__


def is_identifier(identifier):
    """Determines, if string is valid Python identifier."""

    # Smoke test — if it's not string, then it's not identifier, but we don't
    # want to just silence exception. It's better to fail fast.
    if not isinstance(identifier, str):
        raise TypeError('expected str, but got {!r}'.format(type(identifier)))

    # Resulting AST of simple identifier is <Module [<Expr <Name "foo">>]>
    try:
        root = ast.parse(identifier)
    except SyntaxError:
        return False

    if not isinstance(root, ast.Module):
        return False

    if len(root.body) != 1:
        return False

    if not isinstance(root.body[0], ast.Expr):
        return False

    if not isinstance(root.body[0].value, ast.Name):
        return False

    if root.body[0].value.id != identifier:
        return False

    return True


def start_value_from_type(data_type, allow_none=False):
    """Attempt to return a unique "starting value" for a given data type"""
    if not data_type:
        return None

    base_type = data_type[0]

    if base_type in type_factories:
        return type_factories[base_type]()

    elif allow_none:
        return None

    raise TypeError(data_type)


def get_builder_class_args(hive_cls):
    """Find initialiser arguments for builder (bind) class

    :param hive_cls: Hive class
    """
    builder_args = OrderedDict()

    # Find first builder class
    for builder, cls in hive_cls._builders:
        if cls is None:
            continue

        # Same arguments are provided to all bind classes
        break

    else:
        return builder_args

    # Get init func
    init_func = cls.__init__
    arg_types = hive.get_argument_types(init_func)
    arg_options = hive.get_argument_options(init_func)

    arg_spec = getargspec(init_func)
    defaults = arg_spec.defaults if arg_spec.defaults else []

    # Ignore self
    arg_names = arg_spec.args[1:]

    # Populate defaults
    arg_defaults = {}
    for arg_name, default_value in zip(reversed(arg_names), reversed(defaults)):
        arg_defaults[arg_name] = default_value

    # Construct argument pairs
    for arg_name in arg_names:
        arg_data = {'optional': arg_name in arg_defaults, 'default': arg_defaults.get(arg_name),
                    'options': arg_options.get(arg_name), 'data_type': arg_types.get(arg_name, "")}

        builder_args[arg_name] = arg_data

    return builder_args


def get_io_info(hive_object):
    """Get UI info for a runtime hive object"""
    external_bees = hive_object._hive_ex

    inputs = OrderedDict()
    outputs = OrderedDict()

    pin_order = []

    for bee_name in external_bees:
        bee = getattr(external_bees, bee_name)

        # Find IO pins
        exported_bee = bee.export()

        if isinstance(bee, HiveAntenna):
            storage_target = inputs
            data_type = exported_bee.data_type
            mode = exported_bee.mode

        elif isinstance(bee, HiveOutput):
            storage_target = outputs
            data_type = exported_bee.data_type
            mode = exported_bee.mode

        elif isinstance(bee, Hook):
            storage_target = outputs
            data_type = ("trigger",)
            mode = "push"

        elif isinstance(bee, Entry):
            storage_target = inputs
            data_type = ("trigger",)
            mode = "push"

        else:
            continue

        storage_target[bee_name] = dict(data_type=data_type, mode=mode)
        pin_order.append(bee_name)

    return dict(inputs=inputs, outputs=outputs, pin_order=pin_order)


def import_from_path(import_path):
    split_path = import_path.split(".")
    *module_parts, class_name = split_path
    import_path = ".".join(module_parts)
    sub_module_name = module_parts[-1]

    module = __import__(import_path, fromlist=[sub_module_name])

    try:
        return getattr(module, class_name)

    except AttributeError as err:
        raise ImportError from err


def import_path_to_hivemap_path(import_path, additional_paths=None):
    module_path, class_name = import_path.rsplit(".", 1)

    try:
        return find_source_hivemap(module_path, additional_paths)

    except FileNotFoundError:
        raise ValueError


def find_source_hivemap(module_path, additional_paths=()):
    *root_path, module_name = module_path.split(".")

    file_name = "{}.hivemap".format(module_name)
    root_path.append(file_name)

    template_file_path = path.join(*root_path)

    # Most of our interesting files are on sys.path, towards the end
    for directory in chain(additional_paths, reversed(sys.path)):
        file_path = path.join(directory, template_file_path)

        if path.exists(file_path):
            return file_path

    raise FileNotFoundError("No hivemap for '{}' exists".format(module_path))


def create_hive_object_instance(hive_cls, params):
    """Import Hive class from import path, and instantiate it using parameter dictionary

    :param hive_cls: Hive class object
    :param params: parameter dictionary (meta_args, args and cls_args)
    """
    try:
        # Get HiveObject class
        meta_args = params.get("meta_args", {})
        _, _, hive_object_cls = hive_cls._hive_get_hive_object_cls((), meta_args)

        # Get RuntimeHive instance
        args = params.get("args", {}).copy()
        cls_args = params.get("cls_args", {})
        args.update(cls_args)

        return hive_object_cls(**args)

    except Exception as err:
        raise RuntimeError("Unable to instantiate Hive cls {}: {}".format(hive_cls, err))


def camelcase_to_underscores(name):
    s1 = re_sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re_sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def underscore_to_camel_case(name):
    name = name.capitalize()
    return "".join(x.capitalize() if x else '_' for x in name.split("_"))
