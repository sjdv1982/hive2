import sys
from contextlib import contextmanager
from collections import namedtuple
from importlib.machinery import ModuleSpec
from importlib.abc import MetaPathFinder, FileLoader
from os.path import basename, splitext, join, isdir
from os import listdir


from .code_generator import hivemap_to_python_source
from .data_views import ListView
from .utils import underscore_to_camel_case
from .models import model


HivemapLoaderResult = namedtuple("HivemapLoaderResult", "module cls class_name")


class HivemapModuleLoader(FileLoader):
    """Loader for hivemaps"""

    def __init__(self, fullname, path):
        super().__init__(fullname, path)

        self._source = None
        self.results = []

    def clear_cache(self):
        self.results.clear()

    @staticmethod
    def _class_name_from_file_path(file_path):
        file_name = splitext(basename(file_path))[0]
        return underscore_to_camel_case(file_name)

    def get_source(self, fullname):
        return self._source

    def exec_module(self, module):
        name = module.__spec__.name

        # Load hivemap
        hivemap = model.Hivemap.fromfile(self.path)
        class_name = self._class_name_from_file_path(self.path)

        python_source = self._source = hivemap_to_python_source(hivemap, class_name=class_name)

        try:
            exec(python_source, module.__dict__)

        except Exception as exc:
            raise ImportError(name) from exc

        loader_result = HivemapLoaderResult(module, getattr(module, class_name), class_name)
        self.results.append(loader_result)

        return module


class HivemapModuleFinder(MetaPathFinder):
    """MetaPathFinder for hivemaps"""

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

    def find_spec(self, fullname, path, target=None):
        if path is None:
            path = sys.path
            import_path = fullname

        else:
            import_path = fullname.split('.')[-1]

        split_path = import_path.split('.')
        file_name = "{}.hivemap".format(split_path[-1])

        # Search all paths to find hivemap
        for root in path:
            directory = join(root, *split_path[:-1])

            if not isdir(directory):
                continue

            if file_name in listdir(directory):
                file_path = join(directory, file_name)
                break

        else:
            return None

        loader = HivemapModuleLoader(fullname, file_path)
        self._loaders.append(loader)

        spec = ModuleSpec(fullname, loader, origin=file_path, loader_state=None, is_package=False)
        spec.has_location = True

        return spec


_finder = None


def get_hook():
    return _finder


@contextmanager
def sys_path_add_context(path):
    """Add an entry to sys path, and cleanup on exit"""
    if path in sys.path:
        return

    sys.path.append(path)
    yield
    sys.path.remove(path)


def install_hook():
    global _finder
    if _finder is not None:
        raise RuntimeError("Import hook already installed!")

    _finder = HivemapModuleFinder()
    sys.meta_path.append(_finder)

    return _finder


def uninstall_hook():
    global _finder
    if _finder is None:
        raise RuntimeError("Import hook has not yet been installed!")

    sys.meta_path.remove(_finder)

    _finder = None


def clear_imported_hivemaps():
    to_remove = [name for name, module in sys.modules.items() if module_is_hivemap(module)]

    for name in to_remove:
        del sys.modules[name]


def module_is_hivemap(module):
    """Return True if module is a generated module for a hivemap"""
    return isinstance(module.__loader__, HivemapModuleLoader)
