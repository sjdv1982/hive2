import os
import hive

from inspect import isclass, getmembers


def recurse(base_import_path, modules):
    """Recursively find hive names from module path

    Write to dict the qualified name of the package, with a set of Hive class names

    E.g "dragonfly/std/buffer/Buffer" -> {"dragonfly": {"std": {"Buffer", }}}

    :param base_import_path: base path to import module
    :param modules: dict to write to
    """
    # Find filepath of base path
    _split_base_path = base_import_path.split('.')
    _root_mod = __import__(base_import_path, fromlist=[_split_base_path[-1]])
    root_path = os.path.dirname(_root_mod.__file__)

    # Find all members
    for file_name in os.listdir(root_path):
        if file_name.startswith("_"):
            continue

        file_path = os.path.join(root_path, file_name)
        if file_name.endswith(".py"):

            module_name = file_name[:-3]
            import_path = base_import_path + "." + module_name

            module = __import__(import_path, fromlist=[module_name])

            # Find submodule dict
            sub_modules = modules

            *component_path, package_name, module_name = import_path.split('.')
            for component in component_path:
                try:
                    sub_modules = sub_modules[component]

                except KeyError:
                    sub_modules[component] = sub_modules = {}

            # Get set of hive names
            try:
                hive_set = sub_modules[package_name]

            except KeyError:
                hive_set = sub_modules[package_name] = set()

            for name, value in getmembers(module):
                if isclass(value) and issubclass(value, hive.HiveBuilder):

                    hive_set.add(name)

        elif os.path.isdir(file_path):
            import_path = base_import_path + "." + file_name
            recurse(import_path, modules)


def get_bee_names():
    return ()

# TODO add import hook / callback / list for injecting additional hives


def get_hives():
    modules = {}
    recurse("dragonfly", modules)
    return modules