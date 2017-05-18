from .models import model
from .utils import hive_import_from_path


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


def parameter_group_dict_to_array(params):
    return [model.InstanceParameterGroup(n, parameter_dict_to_array(p)) for n, p in params.items()]


def parameter_group_array_to_dict(parameter_group_array):
    return {g.identifier: parameter_array_to_dict(g.params) for g in parameter_group_array}


def parameter_array_to_dict(array):
    return {p.identifier: _eval_spyder_string(p.data_type, p.value) for p in array}


def parameter_dict_to_array(parameters):
    return [model.InstanceParameter(name, _get_type_name(value), repr(value)) for name, value in parameters.items()]


io_reference_path = {"hive.hook", "hive.entry", "hive.antenna", "hive.output"}
wraps_attribute_reference_paths = {"hive.pull_in", "hive.push_in", "hive.push_out", "hive.pull_out"}
wrapper_reference_paths = io_reference_path | wraps_attribute_reference_paths


def hivemap_to_python_source(hivemap, class_name, builder_name="builder"):
    """Generate Hive builder from Hivemap

    :param hivemap: Hivemap instance
    :param class_name: name of class
    :param builder_name: name of builder function
    """
    if not class_name.isidentifier():
        raise ValueError("Class name must be a Python identifier, not '{}'".format(class_name))

    if not builder_name.isidentifier():
        raise ValueError("Builder name must be a Python identifier, not '{}'".format(builder_name))

    bees = {}
    # Add hive and hive_gui to support declarations and hivemap import machinery
    additional_imports = set()
    required_imports = ["hive_editor", "hive"]

    declaration_body = []

    wraps_attribute = []
    attribute_name_to_wrapper = {}

    # Build hives
    for spyder_bee_node in hivemap.nodes:
        identifier = spyder_bee_node.identifier
        reference_path = spyder_bee_node.reference_path

        # Get params
        params = parameter_group_array_to_dict(spyder_bee_node.parameter_groups)

        # Handle HIVE nodes
        if spyder_bee_node.family == "HIVE":
            # Add import path to import set
            root, cls = reference_path.rsplit(".", 1)
            additional_imports.add(root)

            # Find Hive class and inspect it
            try:
                import_result = hive_import_from_path(reference_path)

            except (ImportError, AttributeError):
                raise ValueError("Invalid reference path: {}".format(reference_path))

            args = params.get("args", {})
            cls_args = params.get("cls_args", {})

            # A pre-configured meta-hive
            if import_result.is_meta_primitive:
                all_args = args.copy()
                all_args.update(cls_args)

                all_arg_pairs = ", ".join(["{}={}".format(k, repr(v)) for k, v in all_args.items()])
                statement = "i.{} = {}({})".format(identifier, reference_path, all_arg_pairs)

            else:
                hive_cls = import_result.cls

                is_meta_hive = bool(hive_cls._declarators)
                is_dyna_hive = hive_cls._is_dyna_hive

                meta_args = params.get("meta_args", {})

                # Two stage instantiation (an unconfigured meta hive)
                if is_meta_hive and not is_dyna_hive:
                    non_meta_args = args.copy()
                    non_meta_args.update(cls_args)
                    meta_arg_pairs = ", ".join(["{}={}".format(k, repr(v)) for k, v in meta_args.items()])
                    arg_pairs = ", ".join(["{}={}".format(k, repr(v)) for k, v in non_meta_args.items()])
                    statement = "i.{} = {}({})({})".format(identifier, reference_path, meta_arg_pairs, arg_pairs)

                # One stage instantiation (a dyna/normal hive)
                else:
                    all_args = meta_args.copy()
                    all_args.update(args)
                    all_args.update(cls_args)

                    all_arg_pairs = ", ".join(["{}={}".format(k, repr(v)) for k, v in all_args.items()])
                    statement = "i.{} = {}({})".format(identifier, reference_path, all_arg_pairs)

            declaration_body.append(statement)

        # Handle BEE nodes
        elif spyder_bee_node.family == "BEE":
            bees[identifier] = spyder_bee_node

            # Bees that have to be resolved later
            if reference_path in wrapper_reference_paths:
                # If bee wraps an attribute
                if reference_path in wraps_attribute_reference_paths:
                    wraps_attribute.append(spyder_bee_node)

                continue

            # For attribute
            if reference_path == "hive.attribute":
                meta_args = params['meta_args']
                data_type = meta_args['data_type']

                args = params['args']
                start_value = args['start_value']

                if args['export']:
                    wrapper_name = "ex"

                else:
                    wrapper_name = "i"

                declaration_body.append("{}.{} = hive.attribute('{}', {})"
                                        .format(wrapper_name, identifier, data_type, start_value))
                attribute_name_to_wrapper[identifier] = wrapper_name

            # For modifier
            elif reference_path == "hive.modifier":
                args = params['args']
                code = args['code']

                code_body = "\n    ".join(code.split("\n"))
                statement = """def {}(self):\n    {}\n""".format(identifier, code_body)
                declaration_body[:0] = statement.split("\n")
                declaration_body.append("i.{0} = hive.modifier({0})".format(identifier))

            elif reference_path == "hive.triggerfunc":
                declaration_body.append("i.{} = hive.triggerfunc()".format(identifier))

        else:
            raise ValueError(spyder_bee_node.family)

    # Second Bee pass (For attribute wrappers)
    for spyder_bee_node in wraps_attribute:
        reference_path = spyder_bee_node.reference_path
        params = parameter_group_array_to_dict(spyder_bee_node.parameter_groups)

        # Get attribute
        meta_args = params['meta_args']
        attribute_name = meta_args['attribute_name']
        attribute_wrapper = attribute_name_to_wrapper[attribute_name]

        declaration_body.append("i.{} = {}({}.{})".format(spyder_bee_node.identifier, reference_path, attribute_wrapper,
                                                          attribute_name))

    # At this point, wrappers have attribute, modifier, triggerfunc, pullin, pullout, pushin, pushout
    io_definitions = []

    # Define connections
    connectivity_body = []
    for connection in hivemap.connections:
        from_identifier = connection.from_node
        to_identifier = connection.to_node

        # From a HIVE
        if from_identifier not in bees:
            source_path = "i.{}.{}".format(from_identifier, connection.output_name)

            is_pre_trigger = False

        # From a BEE
        else:
            from_bee = bees[from_identifier]

            # Do antenna, entry definitions later
            if from_bee.reference_path in io_reference_path:
                io_definitions.append(connection)
                continue

            # Here bee can be triggerfunc [trigger, pretrigger] or a push in/out [pre, post update value]]
            source_path = "i.{}".format(from_identifier)
            is_pre_trigger = "pre" in connection.output_name  # HACK XXX

        if to_identifier not in bees:
            target_path = "i.{}.{}".format(to_identifier, connection.input_name)

        # From a BEE
        else:
            to_bee = bees[to_identifier]

            # Do output, hook definitions later
            if to_bee.reference_path in io_reference_path:
                io_definitions.append(connection)
                continue

            # Here bee can be modifier[trigger], ppio[trigger,value]
            target_path = "i.{}".format(to_identifier)

        if connection.is_trigger:
            connectivity_body.append("hive.trigger({}, {}, pretrigger={})".format(source_path, target_path, is_pre_trigger))

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
            if io_bee.reference_path in io_reference_path:
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
            if io_bee.reference_path in io_reference_path:
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

        io_body.append("ex.{} = {}({})".format(wrapper_bee.identifier, wrapper_bee.reference_path, target_path))

    body_declaration_statement = ""

    docstring = hivemap.docstring

    if docstring:
        new_line = "\n" if "\n" in docstring else ""
        # Escape quotation characters
        escaped_docstring = docstring.replace("\"", r'\"')
        body_declaration_statement += '"""{}{}"""\n'.format(escaped_docstring, new_line)

    if declaration_body:
        body_declaration_statement += "# Declarations\n{}\n\n".format("\n".join(declaration_body))

    if connectivity_body:
        body_declaration_statement += "# Connectivity\n{}\n\n".format("\n".join(connectivity_body))

    if io_body:
        body_declaration_statement += "# IO\n{}\n\n".format("\n".join(io_body))

    all_imports = required_imports + list(additional_imports)

    if all_imports:
        import_statement = "# Imports\n{}\n".format("\n".join(["import {}".format(x) for x in all_imports]))

    else:
        import_statement = ""

    # Allow empty hives to be built
    if not body_declaration_statement:
        builder_body = "pass"

    else:
        builder_body = body_declaration_statement.replace("\n", "\n    ")

    declaration_statement = ("{imports}\n\ndef {builder_name}(i, ex, args):\n    {builder_body}\n"
                             "{class_name} = hive.hive('{class_name}', builder={builder_name})"
                             .format(imports=import_statement, builder_name=builder_name, builder_body=builder_body,
                                     class_name=class_name))
    return declaration_statement