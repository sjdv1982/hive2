import os
from collections import namedtuple
from fnmatch import filter
from inspect import isclass, getmembers
from importlib import import_module

import dragonfly
import hive


GUI_CONF_FILENAME = "robots.txt"

_hive_lib_dir = os.path.dirname(dragonfly.__path__[0])
all_bees = ['hive.attribute', 'hive.antenna', 'hive.output', 'hive.entry', 'hive.hook', 'hive.triggerfunc',
            'hive.modifier', 'hive.pull_in', 'hive.pull_out', 'hive.push_in', 'hive.push_out']

FinderPathElement = namedtuple("FinderPathElement", "name file_path")


class HiveFinder:
    """Search utility to find Hive classes in a filesystem"""

    def __init__(self, *additional_paths):
        self._root_paths = {_hive_lib_dir, }
        self.additional_paths = set(additional_paths)

        self._path_to_hives = None
        self._all_hives = None

    @staticmethod
    def create_initial_search_path(path):
        return FinderPathElement(None, path),

    @property
    def all_hives(self):
        return self._all_hives.copy()

    @property
    def hives_by_path(self):
        return self._path_to_hives.copy()

    def _recurse(self, search_path, results=None, _tracked_classes=None):
        """Recursively find hive names from module path.

        Write to dict the qualified name of the package, with a set of Hive class names.
        Root values (Hives) are identified by None values.

        E.g "dragonfly/std/buffer/Buffer" -> {"dragonfly": {"std": {"Buffer": None}}}

        :param search_path: tuple of FinderPathEntry items (first element is root, name unused)
        :param results: dictionary of modules to write to
        :param _tracked_classes: set of found classes (to avoid revisiting)
        """
        assert search_path, "Invalid start path"
        assert isinstance(search_path, tuple), "Search path must be immutable"

        # Initialise data
        if results is None:
            results = []

        if _tracked_classes is None:
            _tracked_classes = set()

        current_entry = search_path[-1]
        current_module_path = current_entry.file_path

        # Current search path names
        root_entry, *following_root = search_path
        assert root_entry.name is None, "Default search path must be created from create_initial_search_path"

        names_from_root = tuple(p.name for p in following_root)

        print("Searching {}".format(current_module_path))
        all_file_names = os.listdir(current_module_path)

        # Allow hiding of files from HIVE GUI
        try:
            with open(os.path.join(current_module_path, GUI_CONF_FILENAME)) as robots:
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

            elif extension not in {".py", ".hivemap"}:
                continue

            names_to_module = names_from_root + (name,)
            import_path = '.'.join(names_to_module)

            # Import the module
            try:
                module = import_module(import_path)

            except ImportError as err:
                print("Couldn't import {}".format(import_path))
                import traceback

                traceback.print_exc()
                continue

            # Search module members
            for name, value in sorted(getmembers(module)):
                if not isclass(value):
                    continue

                if name.startswith('_'):
                    continue

                if value in _tracked_classes:
                    continue

                if not ((issubclass(value, hive.HiveBuilder) and value is not hive.HiveBuilder) or
                        (issubclass(value, hive.MetaHivePrimitive) and value is not hive.MetaHivePrimitive)):
                    continue

                hive_reference_path = '{}.{}'.format(import_path, name)
                results.append(hive_reference_path)
                _tracked_classes.add(value)

            # Recurse to child directory
            if is_directory:
                new_path_entry = FinderPathElement(file_name, current_file_path)
                new_search_path = search_path + (new_path_entry,)
                self._recurse(new_search_path, results, _tracked_classes)

        return results

    def reload(self):
        path_to_hives = {}
        all_hives = []

        # Import stdlib modules
        for base_directory_path in self._root_paths | self.additional_paths:
            path_to_hives[base_directory_path] = path_hives = []
            search_path = self.create_initial_search_path(base_directory_path)
            self._recurse(search_path, results=path_hives)

            # Update total hives too
            all_hives.extend(path_hives)

        self._path_to_hives = path_to_hives
        self._all_hives = all_hives
