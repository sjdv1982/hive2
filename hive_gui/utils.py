import hive
from hive.mixins import *

from .models import model

from collections import OrderedDict


def get_ui_info(run_hive, allow_derived=False):
    """Get UI info for a runtime hive object"""
    hive_object = run_hive._hive_object
    external_bees = hive_object._hive_ex

    inputs = OrderedDict()
    outputs = OrderedDict()

    if allow_derived:
        connect_target_type = ConnectTargetBase
        connect_source_type = ConnectSourceBase

    else:
        connect_target_type = ConnectTarget
        connect_source_type = ConnectSource

    for bee_name in sorted(external_bees):
        bee = getattr(external_bees, bee_name)

        # Find IO pins
        exported_bee = bee.export()

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

    frozen_args_wrapper = hive_object._hive_args_frozen
    builder_args_wrapper = hive_object._hive_parent_class._hive_args
    args = {k: {'value': getattr(frozen_args_wrapper, k),
                'data_type': getattr(builder_args_wrapper, k).data_type} for k in frozen_args_wrapper}

    return dict(inputs=inputs, outputs=outputs, args=args)


_type_map = dict(str=str, int=int, float=float, bool=bool)


def eval_value(value, data_type):
    base_type = eval(data_type)[0]
    return _type_map[base_type](value)


def import_from_path(path):
    split_path = path.split(".")
    *module_parts, class_name = split_path
    import_path = ".".join(module_parts)
    sub_module_name = module_parts[-1]

    module = __import__(import_path, fromlist=[sub_module_name])
    return getattr(module, class_name)


def builder_from_hivemap(data):
    """Create Hive builder from hivemap string

    :param data: string representation of hivemap
    """
    hivemap = model.Hivemap(data)

    def builder(i, ex, args):
        hive_bees = {}

        for bee in hivemap.bees:
            params = {p.identifier: eval_value(p.value, p.data_type) for p in bee.args}
            bee_cls = import_from_path(bee.import_path)
            hive_bee = bee_cls(**params)

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