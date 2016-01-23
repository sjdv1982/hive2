import os
import sys
import types
from contextlib import contextmanager

from .code_generator import class_from_filepath
from .list_view import ListView
from .utils import find_source_hivemap


class HiveModuleLoader:

    def __init__(self, path, context):
        self.path = path
        self.context = context
        self.classes = set()

    def clear_cache(self):
        self.classes.clear()

    def load_module(self, module_path):
        with self.context:
            if module_path not in sys.modules:
                try:
                    cls = class_from_filepath(self.path)

                except Exception as exc:
                    raise ImportError from exc

                self.classes.add(cls)

                try:
                    package, _ = module_path.rsplit('.', 1)

                except ValueError:
                    package = None

                module = types.ModuleType(module_path, cls.__doc__)
                module.__file__ = self.path
                module.__loader__ = self
                module.__package__ = package

                setattr(module, cls.__name__, cls)
                sys.modules[module_path] = module

            # TODO does this happen?
            else:
                raise Exception

            return sys.modules[module_path]


class HiveModuleImporter(object):

    def __init__(self):
        self._additional_paths = []
        self._loaders = []

    @property
    def additional_paths(self):
        return ListView(self._additional_paths)

    def invalidate_caches(self):
        for loader in self._loaders:
            loader.clear_cache()

        self._loaders.clear()

    @contextmanager
    def temporary_relative_context(self, *paths):
        _old_paths = self._additional_paths

        self._additional_paths = _old_paths + list(paths)
        yield
        self._additional_paths = _old_paths

    @property
    def loaders(self):
        return ListView(self._loaders)

    def get_path_of_class(self, cls):
        for loader in self._loaders:

            if cls in loader.classes:
                return loader.path

        raise ValueError("Couldn't find class: {}".format(cls))

    def find_module(self, full_name, path=None):
        additional_paths = reversed(self._additional_paths)

        try:
            file_path = find_source_hivemap(full_name, additional_paths)

        except (FileNotFoundError, ValueError):
            return

        # Allow relative imports to this module using temporary import context
        directory = os.path.dirname(file_path)
        context = self.temporary_relative_context(directory)

        loader = HiveModuleLoader(file_path, context=context)#, register_class=self._register_created_class)
        self._loaders.append(loader)

        return loader


_importer = None


def get_hook():
    return _importer


def install_hook():
    global _importer
    if _importer is not None:
        raise RuntimeError("Import hook already installed!")

    _importer = HiveModuleImporter()
    sys.meta_path.append(_importer)
    return _importer


def uninstall_hook():
    global _importer
    if _importer is None:
        raise RuntimeError("Import hook has not yet been installed!")

    sys.meta_path.remove(_importer)

    _importer = None


def clear_imported_hivemaps():
    to_remove = []

    for name, module in sys.modules.items():
        if isinstance(module.__loader__, HiveModuleLoader):
            to_remove.append(name)

    for name in to_remove:
        del sys.modules[name]

    class_from_filepath.cache_clear()
