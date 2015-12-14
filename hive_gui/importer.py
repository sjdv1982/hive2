import os
import sys
import types

from .utils import class_from_filepath, find_source_hivemap


class HiveModuleLoader:

    def __init__(self, path):
        self.path = path

    def load_module(self, name):
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

    def find_module(self, full_name, path=None):
        try:
            file_path = find_source_hivemap(full_name)

        except FileNotFoundError:
            return

        if os.path.exists(file_path):
            return HiveModuleLoader(file_path)


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
