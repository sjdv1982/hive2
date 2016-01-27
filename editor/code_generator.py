from functools import lru_cache
from os import path

import hive
from .models import model
from .utils import import_from_path, underscore_to_camel_case


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
    # Add hive and hive_gui to support declarations and hivemap import machinery
    imports = {"hive", "editor"}

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
        root, cls = import_path.rsplit(".", 1)
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

            declaration_body.append("{}.{} = hive.attribute('{}', {})"
                                    .format(wrapper_name, identifier, data_type, start_value))
            attribute_name_to_wrapper[identifier] = wrapper_name

        # For modifier
        elif import_path == "hive.modifier":
            code = args['code']
            code_body = "\n    ".join(code.split("\n"))
            statement = """def {}(self):\n    {}\n""".format(identifier, code_body)
            declaration_body[:0] = statement.split("\n")
            declaration_body.append("i.{0} = hive.modifier({0})".format(identifier))

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

    # Define connections
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
        new_line = "\n" if "\n" in docstring else ""
        body_declaration_statement += '"""{}{}"""\n'.format(docstring, new_line)

    if declaration_body:
        body_declaration_statement += "# Declarations\n{}\n\n".format("\n".join(declaration_body))

    if connectivity_body:
        body_declaration_statement += "# Connectivity\n{}\n\n".format("\n".join(connectivity_body))

    if io_body:
        body_declaration_statement += "# IO\n{}\n\n".format("\n".join(io_body))

    if imports:
        import_statement = "# Imports\n{}\n".format("\n".join(["import {}".format(x) for x in imports]))

    else:
        import_statement = ""

    # Allow empty hives to be built
    if not body_declaration_statement:
        function_body = "pass"

    else:
        function_body = body_declaration_statement.replace("\n", "\n    ")

    declaration_statement = "{}\n\ndef {}(i, ex, args):\n    {}\n".format(import_statement, builder_name, function_body)
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
    name = underscore_to_camel_case(file_name)

    with open(filepath, "r") as f:
        hivemap = model.Hivemap(f.read())

    return class_from_hivemap(name, hivemap)
