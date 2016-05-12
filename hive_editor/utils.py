import ast

import hive

# IO bees
from hive.hook import Hook
from hive.entry import Entry
from hive.antenna import HiveAntenna
from hive.output import HiveOutput

from collections import OrderedDict, namedtuple
from inspect import signature
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


ArgOption = namedtuple("ArgOption", ("optional", "default", "options", "data_type"))
HiveImportResult = namedtuple("HiveImportResult", "cls is_meta_primitive")


def _get_type_name(value):
    """Helper function

    Used to write the type name to a hive BeeInstanceParameter
    """
    return value.__class__.__name__


def is_identifier(identifier):
    """Determines, if string is valid Python identifier."""
    if not isinstance(identifier, str):
        raise TypeError('Expected string, received {}'.format(type(identifier)))

    # Resulting AST of simple identifier is <Module [<Expr <Name "foo">>]>
    try:
        root = ast.parse(identifier)

    except SyntaxError:
        return False

    if not isinstance(root, ast.Module):
        return False

    if len(root.body) != 1:
        return False

    body = root.body
    if not isinstance(body[0], ast.Expr):
        return False

    value = body[0].value
    if not isinstance(value, ast.Name):
        return False

    if value.id != identifier:
        return False

    return True


def start_value_from_type(data_type):
    """Attempt to return a unique "starting value" for a given data type"""
    as_tuple = hive.identifier_to_tuple(data_type, allow_none=False)
    base_type = as_tuple[0]

    try:
        return type_factories[base_type]()

    except KeyError:
        raise TypeError(data_type)


def get_builder_class_args(hive_cls):
    """Find initialiser arguments for builder (bind) class

    :param hive_cls: Hive class
    """
    builder_args = OrderedDict()

    # For each builder, from the bottom of the heirarchy
    # Find class args and add them to the parameter list
    for builder, builder_class in hive_cls._builders:
        if builder_class is None:
            continue

        # Get init func
        init_func = builder_class.__init__
        arg_types = hive.get_argument_types(init_func)
        arg_options = hive.get_argument_options(init_func)

        cls_signature = signature(builder_class)

        # Construct argument pairs
        for name, parameter in cls_signature.parameters.items():
            if name in builder_args:
                continue

            if parameter.kind in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL):
                continue

            is_optional = parameter.default is not parameter.empty
            default = parameter.default if is_optional else None

            builder_args[name] = ArgOption(optional=is_optional, default=default, options=arg_options.get(name),
                                           data_type=arg_types.get(name))

    return builder_args


def get_io_info(hive_object):
    """Get UI info for a runtime hive object"""
    external_bees = hive_object._hive_ex

    inputs = OrderedDict()
    outputs = OrderedDict()

    pin_order = []

    for bee_name, bee in external_bees._items:
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
            data_type = 'trigger'
            mode = "push"

        elif isinstance(bee, Entry):
            storage_target = inputs
            data_type = 'trigger'
            mode = "push"

        else:
            continue

        storage_target[bee_name] = dict(data_type=data_type, mode=mode)
        pin_order.append(bee_name)

    return dict(inputs=inputs, outputs=outputs, pin_order=pin_order)


def import_module_from_path(import_path):
    split_path = import_path.split(".")
    *module_parts, class_name = split_path
    import_path = ".".join(module_parts)
    sub_module_name = module_parts[-1]

    return __import__(import_path, fromlist=[sub_module_name]), class_name


def hive_import_from_path(import_path):
    module, class_name = import_module_from_path(import_path)

    try:
        cls = getattr(module, class_name)

    except AttributeError as err:
        raise ImportError from err

    is_meta_primitive = issubclass(cls, hive.MetaHivePrimitive)
    assert is_meta_primitive or issubclass(cls, hive.HiveBuilder)

    return HiveImportResult(cls, is_meta_primitive)


def import_path_to_hivemap_path(import_path, additional_paths):
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


def hive_object_instance_from_import_result(import_result, params):
    """Instantiate a hive using a parameter dictionary

    :param import_result: HiveImportResult object (tuple)
    :param params: dictionary of optional (meta_args (if HiveBuilder), args and cls_args)
    """
    try:
        if import_result.is_meta_primitive:
            hive_object_cls = import_result.cls._hive_object_cls

        else:
            # Get HiveObject class
            meta_args = params.get("meta_args", {})
            _, _, hive_object_cls = import_result.cls._hive_get_hive_object_cls((), meta_args)

        # Get RuntimeHive instance
        args = params.get("args", {}).copy()
        cls_args = params.get("cls_args", {})
        args.update(cls_args)

        return hive_object_cls(**args)

    except Exception as err:
        raise RuntimeError("Unable to instantiate Hive class from {}: {}".format(import_result, err))


def camelcase_to_underscores(name):
    s1 = re_sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re_sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def underscore_to_camel_case(name):
    name = name.capitalize()
    return "".join(x.capitalize() if x else '_' for x in name.split("_"))