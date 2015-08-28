import hive
from hive.mixins import *

from .models import model

from collections import OrderedDict
from inspect import getargspec


_type_map = dict(str=str, int=int, float=float, bool=bool, dict=dict, list=list, set=set, tuple=tuple)


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


def infer_type(value, allow_object=False):
    for name, cls in _type_map.items():
        if isinstance(value, cls):
            return name

    if not allow_object:
        raise ValueError(value)

    return value.__class__.__name__


def start_value_from_type(data_type):
    base_type = data_type[0]

    if base_type in _type_map:
        return _type_map[base_type]()

    elif base_type == "object":
        return None

    raise TypeError(data_type)


def get_builder_class_args(hive_cls):
    # Get arg spec for first builder
    builder_args = []
    arg_defaults = {}

    for builder, cls in hive_cls._builders:
        if cls is None:
            continue

        spec = getargspec(cls.__init__)
        defaults = spec.defaults if spec.defaults else []

        # Ignore self
        builder_args = spec.args[1:]

        # Populate defaults
        for arg_name, default_value in zip(reversed(builder_args), reversed(defaults)):
            arg_defaults[arg_name] = default_value

        break

    return OrderedDict((k, {'optional': k in arg_defaults, 'default': arg_defaults.get(k)}) for k in builder_args)


def get_io_info(hive_object, allow_derived=False):
    """Get UI info for a runtime hive object"""
    external_bees = hive_object._hive_ex

    inputs = {}
    outputs = {}

    pin_order = []

    if allow_derived:
        connect_target_type = ConnectTargetBase
        connect_source_type = ConnectSourceBase

    else:
        connect_target_type = ConnectTarget
        connect_source_type = ConnectSource

    for bee_name in external_bees:
        bee = getattr(external_bees, bee_name)

        # Find IO pins
        exported_bee = bee.export()

        # Skip plugins and sockets
        if isinstance(exported_bee, (Plugin, Socket)):
            continue

        if exported_bee.implements(connect_target_type):
            storage_target = inputs

        elif exported_bee.implements(connect_source_type):
            storage_target = outputs

        else:
            continue

        # Find data type and IO mode
        if exported_bee.implements(Antenna) or exported_bee.implements(Output):
            data_type = exported_bee.data_type
            mode = exported_bee.mode

        elif isinstance(exported_bee, hive.HiveObject):
            data_type = ()
            mode = None

        else:
            data_type = ("trigger",)
            mode = "push"

        storage_target[bee_name] = dict(data_type=data_type, mode=mode)
        pin_order.append(bee_name)

    return dict(inputs=inputs, outputs=outputs, pin_order=pin_order)


def import_from_path(path):
    split_path = path.split(".")
    *module_parts, class_name = split_path
    import_path = ".".join(module_parts)
    sub_module_name = module_parts[-1]

    module = __import__(import_path, fromlist=[sub_module_name])
    return getattr(module, class_name)


def create_hive_object_instance(import_path, params):
    try:
        hive_cls = import_from_path(import_path)

    except (ImportError, AttributeError):
        raise ValueError("Invalid import path: {}".format(import_path))

    try:
        # Get HiveObject class
        meta_args = params.get("meta_args", {})
        _, _, hive_object_cls = hive_cls._hive_get_hive_object_cls((), meta_args)

        # Get RuntimeHive instance
        args = params.get("args", {})
        cls_args = params.get("cls_args", {})
        args.update(cls_args)

        return hive_object_cls(**args)

    except Exception as err:
        raise RuntimeError("Unable to instantiate Hive cls {}: {}".format(hive_cls, err))


def parameter_array_to_dict(array):
    return {p.identifier: _eval_spyder_string(p.data_type, p.value) for p in array}


def dict_to_parameter_array(parameters):
    return [model.BeeInstanceParameter(name, _get_type_name(value), repr(value))
            for name, value in parameters.items()]


def builder_from_hivemap(data):
    """Create Hive builder from hivemap string

    :param data: string representation of hivemap
    """
    hivemap = model.Hivemap(data)

    def builder(i, ex, args):
        hive_bees = {}

        for bee in hivemap.bees:
            # Get params
            meta_args = parameter_array_to_dict(bee.meta_args)
            args = parameter_array_to_dict(bee.args)
            cls_args = parameter_array_to_dict(bee.cls_args)

            params = {"meta_args": meta_args, "args": args, "cls_args": cls_args}

            hive_bee = create_hive_object_instance(bee.import_path, params)

            setattr(ex, bee.identifier, hive_bee)
            hive_bees[bee.identifier] = hive_bee

        for connection in hivemap.connections:
            from_bee = hive_bees[connection.from_bee]
            from_output = getattr(from_bee, connection.output_name)

            to_bee = hive_bees[connection.to_bee]
            to_input = getattr(to_bee, connection.input_name)

            hive.connect(from_output, to_input)

    builder.__doc__ = hivemap.docstring
    return builder


def class_from_hivemap(name, data):
    """Build Hive class from hivemap string

    :param name: name of hive class
    :param data: string representation of hivemap
    """
    builder = builder_from_hivemap(data)
    return hive.hive(name, builder)