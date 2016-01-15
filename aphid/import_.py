import os

import editor
import hive


class ImportClass:

    def __init__(self):
        self._hive = hive.get_run_hive()
        self.import_path = None

    def do_import_from_path(self):
        module_parts = self.import_path.split(".")
        sub_module_name = module_parts[-1]

        gui_file_path = os.path.dirname(self._hive.parent._hive_object._hive_parent_class._hive_file_path)
        context = editor.get_hook().temporary_relative_context(gui_file_path)

        with context:
            module = __import__(self.import_path, fromlist=[sub_module_name])

        self._module = module


def build_import(cls, i, ex, args):
    """Interface to python import mechanism, with respect to editor project path"""
    i.import_path = hive.property(cls, "import_path", 'str')
    i.pull_import_path = hive.pull_in(i.import_path)
    ex.import_path = hive.antenna(i.pull_import_path)

    i.do_import = hive.triggerable(cls.do_import_from_path)

    i.module = hive.attribute("module")
    i.pull_module = hive.pull_out(i.module)
    ex.module = hive.output(i.pull_module)

    hive.trigger(i.pull_module, i.pull_import_path, pretrigger=True)
    hive.trigger(i.pull_module, i.do_import, pretrigger=True)

Import = hive.hive("Import", build_import, cls=ImportClass)

