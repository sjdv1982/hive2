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

    def _recurse(self, search_path, modules=None, tracked_classes=None):
        """Recursively find hive names from module path.

        Write to dict the qualified name of the package, with a set of Hive class names.
        Root values (Hives) are identified by None values.

        E.g "dragonfly/std/buffer/Buffer" -> {"dragonfly": {"std": {"Buffer": None}}}

        :param base_file_path: base file path from which search was initialised
        :param relative_folder_path: relative file path to base_file_path of current search
        :param modules: dictionary of modules to write to
        """
        assert search_path, "Invalid start path"
        assert isinstance(search_path, tuple), "Search path must be immutable"

        if modules is None:
            modules = OrderedDict()

        if tracked_classes is None:
            tracked_classes = set()

        print(search_path)

        current_entry = search_path[-1]
        current_module_path = current_entry.file_path

        # Current search path names
        root_entry, *following_root = search_path
        names_from_root = tuple(p.name for p in following_root)

        tracked_module_paths = {p.file_path for p in search_path}

        print("Searching {}...".format(current_module_path))
        all_file_names = os.listdir(current_module_path)

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
                    if value in tracked_classes:
                        continue

                    if (issubclass(value, hive.HiveBuilder) and value is not hive.HiveBuilder) or \
                            (issubclass(value, hive.MetaHivePrimitive) and value is not hive.MetaHivePrimitive):
                        sub_modules[name] = None
                        tracked_classes.add(value)

            # Recurse to child directory, but only if nothing was handled by Python
            if is_directory:
                print("Traverse", current_file_path)
                new_path_entry = FinderPathEntry(file_name, current_file_path)
                new_search_path = search_path + (new_path_entry,)
                self._recurse(new_search_path, modules, tracked_classes)

        return modules

    def _recurse_reference(self, base_file_path, relative_folder_path, modules=None):
        """Recursively find hive names from module path.

        Write to dict the qualified name of the package, with a set of Hive class names.
        Root values (Hives) are identified by None values.

        E.g "dragonfly/std/buffer/Buffer" -> {"dragonfly": {"std": {"Buffer": None}}}

        :param base_file_path: base file path from which search was initialised
        :param relative_folder_path: relative file path to base_file_path of current search
        :param modules: dictionary of modules to write to
        """
        current_folder_path = os.path.join(base_file_path, relative_folder_path)
        all_file_names = os.listdir(current_folder_path)

        print("Searching {}".format(current_folder_path))

        if modules is None:
            modules = OrderedDict()

        # Allow hiding of files from HIVE GUI
        if ROBOTS_TEXT in all_file_names:
            with open(os.path.join(current_folder_path, ROBOTS_TEXT)) as robots:
                lines = [l.strip() for l in robots]

            all_file_names = [filename for pattern in lines for filename in filter(all_file_names, pattern)]
            print("Restricted search to {}".format(all_file_names))

        all_file_names.sort()

        # Find all members
        for file_name in all_file_names:
            if file_name.startswith("_"):
                continue

            current_file_path = os.path.join(current_folder_path, file_name)
            relative_file_path = os.path.join(relative_folder_path, file_name)
            name, extension = os.path.splitext(file_name)

            # Ignore hidden directories
            is_directory = os.path.isdir(current_file_path)
            if is_directory:
                if name.startswith('.'):
                    continue

            # Ignore invalid file types
            elif extension[1:] not in {'py', 'hivemap'}:
                continue

            module_file_path = os.path.join(relative_folder_path, name)
            import_path = module_file_path.replace(os.path.sep, ".")
            print("visit", module_file_path, import_path)
            try:
                module = __import__(import_path, fromlist=[name])

            except ImportError as err:
                print("Couldn't import {}".format(import_path))
                import traceback
                traceback.print_exc()
                continue

            # Find submodule dict
            sub_modules = modules

            for component in import_path.split('.'):
                try:
                    sub_modules = sub_modules[component]

                except KeyError:
                    sub_modules[component] = sub_modules = OrderedDict()

            for name, value in sorted(getmembers(module)):
                if name.startswith('_'):
                    continue

                if isclass(value):
                    if issubclass(value, hive.HiveBuilder) and value is not hive.HiveBuilder:
                        sub_modules[name] = None

                    elif issubclass(value, hive.MetaHivePrimitive) and value is not hive.MetaHivePrimitive:
                        sub_modules[name] = None

                elif ismodule(value):
                    pass

            if is_directory and not sub_modules:
                self._recurse(base_file_path, relative_file_path, modules)

        return modules

    def find_hives(self):
        tree = OrderedDict()

        # Import stdlib modules
        for base_directory_path in self._root_paths | self.additional_paths:
            search_path = FinderPathEntry("<root>", base_directory_path),
            self._recurse(search_path, modules=tree)

        return tree
