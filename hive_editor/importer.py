import sys
from contextlib import contextmanager
from collections import namedtuple
from types import ModuleType
from os.path import basename, splitext

from .code_generator import hivemap_to_python_source
from .data_views import ListView
from .utils import find_source_hivemap, underscore_to_camel_case
from .models import model


HivemapLoaderResult = namedtuple("HivemapLoaderResult", "module cls class_name")


class HivemapModuleLoader:
    """Load Hivemap as Python module"""

    def __init__(self, path):
        self.path = path
        self.results = []

    def clear_cache(self):
        self.results.clear()

    def _class_name_from_file_path(self, file_path):
        file_name = splitext(basename(file_path))[0]
        return underscore_to_camel_case(file_name)

    def load_module(self, module_path):
        if module_path not in sys.modules:
            # Load hivemap
            hivemap = model.Hivemap.fromfile(self.path)
            class_name = self._class_name_from_file_path(self.path)

            python_source = hivemap_to_python_source(hivemap, class_name=class_name)

            try:
                package, _ = module_path.rsplit('.', 1)

            except ValueError:
                package = None

            # Create module
            module = ModuleType(module_path)
            module.__file__ = self.path
            module.__loader__ = self
            module.__package__ = package

            try:
                exec(python_source, module.__dict__)

            except Exception as exc:
                raise ImportError(module_path) from exc

            loader_result = HivemapLoaderResult(module, getattr(module, class_name), class_name)
            self.results.append(loader_result)

            sys.modules[module_path] = module

        # TODO does this happen?
        else:
            raise Exception

        return sys.modules[module_path]


class HivemapModuleImporter(object):

    def __init__(self):
        self._loaders = []

    def invalidate_caches(self):
        for loader in self._loaders:
            loader.clear_cache()

        self._loaders.clear()

    @property
    def loaders(self):
        return ListView(self._loaders)

    def find_loader_result_for_class(self, cls):
        for loader in self._loaders:

            for result in loader.results:
                if result.cls is cls:
                    return result

        raise ValueError("Couldn't find class: {}".format(cls))

    def find_module(self, full_name, path=None):
        try:
            file_path = find_source_hivemap(full_name)

        except (FileNotFoundError, ValueError):
            return

        loader = HivemapModuleLoader(file_path)
        self._loaders.append(loader)

        return loader


_importer = None


def get_hook():
    return _importer


@contextmanager
def sys_path_add_context(path):
    """Add an entry to sys path, and cleanup on exit"""
    if path in sys.path:
        return

    sys.path.append(path)
    yield
    sys.path.remove(path)


def install_hook():
    global _importer
    if _importer is not None:
        raise RuntimeError("Import hook already installed!")

    _importer = HivemapModuleImporter()
    sys.meta_path.append(_importer)

    return _importer


def uninstall_hook():
    global _importer
    if _importer is None:
        raise RuntimeError("Import hook has not yet been installed!")

    sys.meta_path.remove(_importer)

    _importer = None


def clear_imported_hivemaps():
    to_remove = [name for name, module in sys.modules.items() if isinstance(module.__loader__, HivemapModuleLoader)]

    for name in to_remove:
        del sys.modules[name]
