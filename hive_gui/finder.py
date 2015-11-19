import sys
import os
import hive
import dragonfly

from inspect import isclass, getmembers, ismodule

from .importer import install_hook
install_hook()


found_bees = {"hive": ["attribute", "antenna", "output", "entry", "hook", "triggerfunc", "modifier", "pull_in", "pull_out",
                       "push_in", "push_out"]}


class HiveFinder:

    def __init__(self, *root_paths):
        paths = list(root_paths)
        paths.append(dragonfly.__path__[0])
        self.root_paths = paths

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

            if extension[1:] in {'py', 'hivemap'}:
                module_file_path = os.path.join(base_folder_name, relative_folder_path, name)
                import_path = module_file_path.replace(os.path.sep, ".")

                module = __import__(import_path, fromlist=[import_path])

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
                    if name.startswith('_'):
                        continue

                    if isclass(value) and issubclass(value, hive.HiveBuilder):
                        hive_set.add(name)

            elif os.path.isdir(current_file_path):
                self._recurse(base_file_path, relative_file_path, modules)

    def find_hives(self):
        filesystem = {}

        for root_path in self.root_paths:
            if root_path not in sys.path:
                sys.path.append(root_path)

            self._recurse(root_path, '', filesystem)

        return filesystem