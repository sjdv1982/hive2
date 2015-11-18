import sys
import os
import types

from .utils import class_from_filepath


class HiveModuleLoader:

    def __init__(self, path):
        self.path = path

    def load_module(self, name):
        if name not in sys.modules:
            cls = class_from_filepath(self.path)
            module = types.ModuleType(name, cls.__doc__)
            setattr(module, cls.__name__, cls)
            sys.modules[name] = module

        return sys.modules[name]


class HiveModuleImporter(object):

    def find_module(self, fullname, path=None):
        for directory in sys.path:
            file_name = os.path.join(directory, "{}.hivemap".format(fullname))

            if os.path.exists(file_name):
                return HiveModuleLoader(file_name)

        return None


def install_hook():
    sys.meta_path.append(HiveModuleImporter())
