import os
from collections import OrderedDict, namedtuple
from fnmatch import filter
from inspect import isclass, ismodule, getmembers

import dragonfly
import hive


def _keys_to_dict(keys):
    return OrderedDict([(k, None) for k in keys])


_hive_lib_dir = os.path.dirname(dragonfly.__path__[0])
found_bees = {"hive": _keys_to_dict(["attribute", "antenna", "output", "entry", "hook", "triggerfunc", "modifier",
                                     "pull_in", "pull_out", "push_in", "push_out"])}

ROBOTS_TEXT = "robots.txt"
FinderPathEntry = namedtuple("FinderPair", "name file_path")


class HiveFinder:
    """Search utility to find Hive classes in a filesystem"""

    def __init__(self, *additional_paths):
        self._root_paths = {_hive_lib_dir, }
        self.additional_paths = set(additional_paths)

    @staticmethod
    def create_initial_search_path(path):
        return FinderPathEntry(None, path),

    def _recurse(self, search_path, modules=None, _tracked_classes=None):
        """Recursively find hive names from module path.

        Write to dict the qualified name of the package, with a set of Hive class names.
        Root values (Hives) are identified by None values.

        E.g "dragonfly/std/buffer/Buffer" -> {"dragonfly": {"std": {"Buffer": None}}}

        :param search_path: tuple of FinderPathEntry items (first element is root, name unused)
        :param modules: dictionary of modules to write to
        :param _tracked_classes: set of found classes (to avoid revisiting)
        """
        assert search_path, "Invalid start path"
        assert isinstance(search_path, tuple), "Search path must be immutable"

        current_entry = search_path[-1]
        current_module_path = current_entry.file_path

        # Current search path names
        root_entry, *following_root = search_path
        assert root_entry.name is None, "Default search path must be created from create_initial_search_path"

        names_from_root = tuple(p.name for p in following_root)

        print("Searching {}...".format(current_module_path))
        all_file_names = os.listdir(current_module_path)

        # Initialse data
        if modules is None:
            modules = OrderedDict()

        if _tracked_classes is None:
            _tracked_classes = set()

        # Allow hiding of files from HIVE GUI
        try:
            with open(os.path.join(current_module_path, ROBOTS_TEXT)) as robots:
                lines = [l.strip() for l in robots]

            all_file_names = [filename for pattern in lines for filename in filter(all_file_names, pattern)]
            print("Restricted search to {}".format(all_file_names))

        except FileNotFoundError:
            pass

        all_file_names.sort()

        # Find all members
        for file_name in all_file_names:
            if file_name.startswith("_"):
                continue

            current_file_path = os.path.join(current_module_path, file_name)
            name, extension = os.path.splitext(file_name)

            # Ignore hidden directories
            is_directory = os.path.isdir(current_file_path)
            if is_directory:
                if name.startswith('.'):
                    continue

            # Ignore invalid file types
            elif extension[1:] not in {'py', 'hivemap'}:
                continue

            names_to_module = names_from_root + (name,)
            import_path = '.'.join(names_to_module)

            # Import the module
            try:
                module = __import__(import_path, fromlist=[name])

            except ImportError as err:
                print("Couldn't import {}".format(import_path))
                import traceback

                traceback.print_exc()
                continue

            # Get (/create) sub module dict
            sub_modules = modules

            for entry_name in names_to_module:
                try:
                    sub_modules = sub_modules[entry_name]

                except KeyError:
                    sub_modules[entry_name] = sub_modules = OrderedDict()

            # Search module members
            for name, value in sorted(getmembers(module)):
                if name.startswith('_'):
                    continue

                if isclass(value):
                    if value in _tracked_classes:
                        continue

                    if (issubclass(value, hive.HiveBuilder) and value is not hive.HiveBuilder) or \
                            (issubclass(value, hive.MetaHivePrimitive) and value is not hive.MetaHivePrimitive):
                        sub_modules[name] = None
                        _tracked_classes.add(value)

            # Recurse to child directory, but only if nothing was handled by Python
            if is_directory:
                print("Traverse", current_file_path)
                new_path_entry = FinderPathEntry(file_name, current_file_path)
                new_search_path = search_path + (new_path_entry,)
                self._recurse(new_search_path, modules, _tracked_classes)

        return modules

    def find_hives(self):
        tree = OrderedDict()

        # Import stdlib modules
        for base_directory_path in self._root_paths | self.additional_paths:
            search_path = self.create_initial_search_path(base_directory_path)
            self._recurse(search_path, modules=tree)

        return tree
