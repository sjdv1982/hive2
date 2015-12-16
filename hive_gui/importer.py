import os
import sys
import types
from contextlib import contextmanager

from .code_generator import class_from_filepath
from .utils import find_source_hivemap


class HiveModuleLoader:

    def __init__(self, path, context):
        self.path = path
        self.context = context

    def load_module(self, name):
        with self.context:
            if name not in sys.modules:
                try:
                    cls = class_from_filepath(self.path)

                except Exception as exc:
                    raise ImportError from exc

                module = types.ModuleType(name, cls.__doc__)
                module.__file__ = self.path
                module.__loader__ = self

                setattr(module, cls.__name__, cls)
                sys.modules[name] = module

            return sys.modules[name]


class HiveModuleImporter(object):

    def __init__(self):
        self._additional_paths = []

    @contextmanager
    def temporary_relative_context(self, *paths):
        _old_paths = self._additional_paths
        self._additional_paths = _old_paths + list(paths)
        yield
        self._additional_paths = _old_paths

    def find_module(self, full_name, path=None):
        additional_paths = reversed(self._additional_paths)

        try:
            file_path = find_source_hivemap(full_name, additional_paths)

        except (FileNotFoundError, ValueError):
            return

        # Allow relative imports to this module using temporary import context
        directory = os.path.dirname(file_path)
        context = self.temporary_relative_context(directory)

        return HiveModuleLoader(file_path, context=context)


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
