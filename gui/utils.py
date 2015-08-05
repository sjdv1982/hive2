import hive
from hive.mixins import *

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

    for bee_name in external_bees:
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
    *module_parts, _ = split_path
    module_name = ".".join(module_parts)

    module = __import__(module_name)

    for part in split_path[1:]:
        module = getattr(module, part)

    return module