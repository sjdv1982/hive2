import os
import sys
from collections import OrderedDict
from inspect import isclass, getmembers

import dragonfly
import hive


def _keys_to_dict(keys):
    return OrderedDict([(k, None) for k in keys])


found_bees = {"hive": _keys_to_dict(["attribute", "antenna", "output", "entry", "hook", "triggerfunc", "modifier",
                                     "pull_in", "pull_out", "push_in", "push_out"])}


class HiveFinder:
    """Search utility to find Hive classes in a filesystem"""

    def __init__(self, *additional_paths):
        self.root_paths = {dragonfly.__path__[0], }
        self.additional_paths = set(additional_paths)
        self._added_paths = set()

    def clear(self):
        for path in self._added_paths:
            sys.path.remove(path)

        self._added_paths.clear()

    def _recurse(self, base_file_path, relative_folder_path, modules):
        """Recursively find hive names from module path

        Write to dict the qualified name of the package, with a set of Hive class names

        E.g "dragonfly/std/buffer/Buffer" -> {"dragonfly": {"std": {"Buffer", }}}

        :param base_import_path: base path to import module
        :param modules: dict to write to
        """
        current_folder_path = os.path.join(base_file_path, relative_folder_path)
        base_folder_name = os.path.basename(base_file_path)

        # Find all members
        for file_name in os.listdir(current_folder_path):
            if file_name.startswith("_"):
                continue

            current_file_path = os.path.join(current_folder_path, file_name)
            relative_file_path = os.path.join(relative_folder_path, file_name)
            name, extension = os.path.splitext(file_name)

            is_directory = os.path.isdir(current_file_path)

            if is_directory or extension[1:] in {'py', 'hivemap'}:
                module_file_path = os.path.join(base_folder_name, relative_folder_path, name)
                import_path = module_file_path.replace(os.path.sep, ".")

                try:
                    module = __import__(import_path, fromlist=[name])

                except ImportError:
                    print("Couldn't import {}".format(import_path))
                    continue

                # Find submodule dict
                sub_modules = modules

                for component in import_path.split('.'):
                    try:
                        sub_modules = sub_modules[component]

                    except KeyError:
                        sub_modules[component] = sub_modules = OrderedDict()

                for name, value in getmembers(module):
                    if name.startswith('_'):
                        continue

                    if isclass(value) and issubclass(value, hive.HiveBuilder):
                        sub_modules[name] = None

                if is_directory and not sub_modules:
                    self._recurse(base_file_path, relative_file_path, modules)

    def find_hives(self):
        self.clear()

        filesystem = {}

        # Import stdlib modules
        for root_path in self.root_paths:
            self._recurse(root_path, '', filesystem)

        # Keep track of added paths to sys path
        for additional_path in self.additional_paths:
            if additional_path not in sys.path:
                sys.path.append(additional_path)
                self._added_paths.add(additional_path)

            self._recurse(additional_path, '', filesystem)

        return filesystem
