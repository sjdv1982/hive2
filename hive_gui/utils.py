import ast

import hive
from hive.mixins import *
# IO bees
from hive.hook import Hook
from hive.entry import Entry
from hive.antenna import HiveAntenna
from hive.output import HiveOutput

from .models import model

from collections import OrderedDict
from inspect import getargspec
from functools import lru_cache
from os import path
from re import sub as re_sub
import sys

# Factories for types
type_factories = {}
type_factories["vector"] = lambda: (0.0, 0.0, 0.0)
type_factories["colour"] = lambda: (0.0, 0.0, 0.0)
type_factories["str"] = str
type_factories["bool"] = bool
type_factories["int"] = int
type_factories["float"] = float
type_factories["tuple"] = tuple
type_factories["list"] = list
type_factories["dict"] = dict
type_factories["set"] = set


def _eval_spyder_string(type_name, value):
    """Helper function

    Writing repr'd strings to Spyder String objects will remove the leading apostrophe,
    Handle this case explicitly before calling eval
    """
    if type_name == "str":
        return str(value)

    return eval(value)


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


def start_value_from_type(data_type):
    """Attempt to return a unique "starting value" for a given data type"""
    if not data_type:
        return None

    base_type = data_type[0]

    if base_type in type_factories:
        return type_factories[base_type]()

    elif base_type == "object":
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
                    'options': arg_options.get(arg_name), 'data_type': arg_types.get(arg_name, ())}

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

        if exported_bee.implements(ConnectTarget):
            storage_target = inputs

        elif exported_bee.implements(ConnectSource):
            storage_target = outputs

        else:
            continue

        # Find data type and IO mode
        if isinstance(bee, (HiveAntenna, HiveOutput)):
            data_type = exported_bee.data_type
            mode = exported_bee.mode

        elif isinstance(bee, (Hook, Entry)):
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
    return getattr(module, class_name)


def import_path_to_hivemap_path(import_path):
    module_path, class_name = import_path.rsplit(".", 1)

    try:
        return find_source_hivemap(module_path)

    except FileNotFoundError:
        raise ValueError


def find_source_hivemap(module_path):
    try:
        *root_path, module_name = module_path.split(".")

    except ValueError:
        return

    file_name = "{}.hivemap".format(module_name)
    template_file_path = path.join(*root_path, file_name)

    # Most of our interesting files are on sys.path, towards the end
    for directory in reversed(sys.path):
        file_path = template_file_path.format(directory)

        if path.exists(file_path):
            return file_path

    raise FileNotFoundError("No hivemap for '{}' exists".format(module_path))


def create_hive_object_instance(import_path, params):
    """Import Hive class from import path, and instantiate it using parameter dictionary

    :param import_path: path to import Hive class
    :param params: parameter dictionary (meta_args, args and cls_args)
    """
    try:
        hive_cls = import_from_path(import_path)

    except (ImportError, AttributeError):
        raise ValueError("Invalid import path: {}".format(import_path))

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


def parameter_array_to_dict(array):
    return {p.identifier: _eval_spyder_string(p.data_type, p.value) for p in array}


def dict_to_parameter_array(parameters):
    return [model.InstanceParameter(name, _get_type_name(value), repr(value)) for name, value in parameters.items()]


_io_import_paths = {"hive.hook", "hive.entry", "hive.antenna", "hive.output"}
_wraps_attribute_import_paths = {"hive.pull_in", "hive.push_in", "hive.push_out", "hive.pull_out"}
_wrapper_import_paths = _io_import_paths | _wraps_attribute_import_paths


def hivemap_to_builder_body(hivemap, builder_name="builder"):
    """Generate Hive builder from Hivemap

    :param hivemap: Hivemap instance
    :param builder_name: name of builder function
    """
    bees = {}
    imports = {"hive", }

    declaration_body = []

    # Build hives
    for spyder_hive in hivemap.hives:
        hive_name = spyder_hive.identifier

        # Get params
        meta_args = parameter_array_to_dict(spyder_hive.meta_args)
        args = parameter_array_to_dict(spyder_hive.args)
        cls_args = parameter_array_to_dict(spyder_hive.cls_args)

        # Add import path to import set
        import_path = spyder_hive.import_path
        root, *_ = import_path.split(".")
        imports.add(root)

        # Find Hive class and inspect it
        try:
            hive_cls = import_from_path(import_path)

        except (ImportError, AttributeError):
            raise ValueError("Invalid import path: {}".format(import_path))

        is_meta_hive = bool(hive_cls._declarators)
        is_dyna_hive = hive_cls._is_dyna_hive

        # Two stage instantiation
        if is_meta_hive and not is_dyna_hive:
            non_meta_args = args.copy()
            non_meta_args.update(cls_args)
            meta_arg_pairs = ", ".join(["{}={}".format(k, repr(v)) for k, v in meta_args.items()])
            arg_pairs = ", ".join(["{}={}".format(k, repr(v)) for k, v in non_meta_args.items()])
            statement = "i.{} = {}({})()".format(hive_name, import_path, meta_arg_pairs, arg_pairs)

        # One stage instantiation
        else:
            all_args = meta_args.copy()
            all_args.update(args)
            all_args.update(cls_args)

            all_arg_pairs = ", ".join(["{}={}".format(k, repr(v)) for k, v in all_args.items()])
            statement = "i.{} = {}({})".format(hive_name, import_path, all_arg_pairs)

        declaration_body.append(statement)

    wraps_attribute = []
    attribute_name_to_wrapper = {}

    # First pass bees (Standalone bees)
    for spyder_bee in hivemap.bees:
        import_path = spyder_bee.import_path
        identifier = spyder_bee.identifier

        bees[identifier] = spyder_bee

        # Bees that have to be resolved later
        if import_path in _wrapper_import_paths:
            # If bee wraps an attribute
            if import_path in _wraps_attribute_import_paths:
                wraps_attribute.append(spyder_bee)

            continue

        # Get params
        meta_args = parameter_array_to_dict(spyder_bee.meta_args)
        args = parameter_array_to_dict(spyder_bee.args)

        # For attribute
        if import_path == "hive.attribute":
            data_type = meta_args['data_type']
            start_value = args['start_value']

            if args['export']:
                wrapper_name = "ex"

            else:
                wrapper_name = "i"

            declaration_body.append("{}.{} = hive.attribute({}, {})"
                                    .format(wrapper_name, identifier, data_type, start_value))
            attribute_name_to_wrapper[identifier] = wrapper_name

        # For modifier
        elif import_path == "hive.modifier":
            code = args['code']
            code_body = "\n    ".join(code.split("\n"))
            statement = """def {}(self):\n    {}""".format(identifier, code_body)
            declaration_body.extend(statement.split("\n"))
            declaration_body.append("i.{0} = hive.modifier({0})\n".format(identifier))

        elif import_path == "hive.triggerfunc":
            declaration_body.append("i.{} = hive.triggerfunc()".format(identifier))

    # Second Bee pass (For attribute wrappers)
    for spyder_bee in wraps_attribute:
        import_path = spyder_bee.import_path

        meta_args = parameter_array_to_dict(spyder_bee.meta_args)

        # Get attribute
        attribute_name = meta_args['attribute_name']
        attribute_wrapper = attribute_name_to_wrapper[attribute_name]

        declaration_body.append("i.{} = {}({}.{})".format(spyder_bee.identifier, import_path,
                                                          attribute_wrapper, attribute_name))

    # At this point, wrappers have attribute, modifier, triggerfunc, pullin, pullout, pushin, pushout
    io_definitions = []

    # Define connectons
    connectivity_body = []
    for connection in hivemap.connections:
        from_identifier = connection.from_node
        to_identifier = connection.to_node

        pretrigger = False

        # From a HIVE
        if from_identifier not in bees:
            source_path = "i.{}.{}".format(from_identifier, connection.output_name)

        # From a BEE
        else:
            from_bee = bees[from_identifier]

            # Do antenna, entry definitions later
            if from_bee.import_path in _io_import_paths:
                io_definitions.append(connection)
                continue

            # Here bee can be triggerfunc[trigger,pretrigger, ppio[pre,post,value]
            source_path = "i.{}".format(from_identifier)

            # If pretrigger
            if "pre" in connection.output_name:
                pretrigger = True

        if to_identifier not in bees:
            target_path = "i.{}.{}".format(to_identifier, connection.input_name)

        # From a BEE
        else:
            to_bee = bees[to_identifier]

            # Do output, hook definitions later
            if to_bee.import_path in _io_import_paths:
                io_definitions.append(connection)
                continue

            # Here bee can be modifier[trigger], ppio[trigger,value]
            target_path = "i.{}".format(to_identifier)

        if connection.is_trigger:
            connectivity_body.append("hive.trigger({}, {}, pretrigger={})".format(source_path, target_path, pretrigger))

        else:
            connectivity_body.append("hive.connect({}, {})".format(source_path, target_path))

    # Define IO pins (antenna, entry, output, hook)
    io_body = []
    for connection in io_definitions:
        from_identifier = connection.from_node
        to_identifier = connection.to_node

        wrapper_bee = None
        target_path = None

        # From a BEE
        if from_identifier in bees:
            io_bee = bees[from_identifier]

            # From an IO BEE
            if io_bee.import_path in _io_import_paths:
                wrapper_bee = io_bee

            # From a generic other bee
            else:
                target_path = "i.{}".format(from_identifier)

        else:
            target_path = "i.{}.{}".format(from_identifier, connection.output_name)

        # To a BEE
        if to_identifier in bees:
            io_bee = bees[to_identifier]

            # To an IO BEE
            if io_bee.import_path in _io_import_paths:
                assert wrapper_bee is None
                wrapper_bee = io_bee

            # To a generic other bee
            else:
                assert target_path is None
                target_path = "i.{}".format(to_identifier)

        # To a hive
        else:
            assert target_path is None
            target_path = "i.{}.{}".format(to_identifier, connection.input_name)

        io_body.append("ex.{} = {}({})".format(wrapper_bee.identifier, wrapper_bee.import_path, target_path))

    body_declaration_statement = ""

    docstring = hivemap.docstring

    if docstring:
        body_declaration_statement += \
'''"""{}"""'''.format(docstring)

    if declaration_body:
        body_declaration_statement += \
"""
# Declarations
{}
""".format("\n".join(declaration_body))

    if connectivity_body:
        body_declaration_statement += \
"""
# Connectivity
{}
""".format("\n".join(connectivity_body))

    if io_body:
        body_declaration_statement += \
"""
# IO
{}
""".format("\n".join(io_body))

    if imports:
        import_statement = \
"""# Imports
{}""".format("\n".join(["import {}".format(x) for x in imports]))
    else:
        import_statement = ""

    # Allow empty hives to be built
    if not body_declaration_statement:
        function_body = "pass"

    else:
        function_body = body_declaration_statement.replace("\n", "\n    ")

    declaration_statement = \
"""{}

def {}(i, ex, args):
    {}
""".format(import_statement, builder_name, function_body)
    return declaration_statement


def builder_from_hivemap(hivemap):
    """Create Hive builder from hivemap

    :param hivemap: Hivemap instance
    """
    build_str = hivemap_to_builder_body(hivemap, builder_name="builder")
    local_dict = dict(globals())
    local_dict.update(locals())

    exec(build_str, local_dict, local_dict)
    return local_dict['builder']


def class_from_hivemap(name, hivemap):
    """Build Hive class from hivemap string

    :param name: name of hive class
    :param hivemap: Hivemap instance
    """
    builder = builder_from_hivemap(hivemap)
    return hive.hive(name, builder)


@lru_cache(maxsize=256)
def class_from_filepath(filepath):
    """Build Hive class from hivemap filepath

    :param filepath: path to hivemap
    """
    file_name = path.splitext(path.basename(filepath))[0]
    name = underscore_to_class_name(file_name)

    with open(filepath, "r") as f:
        hivemap = model.Hivemap(f.read())

    return class_from_hivemap(name, hivemap)


def camelcase_to_underscores(name):
    s1 = re_sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re_sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def underscore_to_class_name(name):
    name = name.capitalize()
    return "".join(x.capitalize() if x else '_' for x in name.split("_"))
