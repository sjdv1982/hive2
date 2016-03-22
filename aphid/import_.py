from contextlib import contextmanager
import os

import hive
import hive_editor


@contextmanager
def _no_context():
    yield
    return


class ImportClass:

    def __init__(self):
        self._hive = hive.get_run_hive()

        self.import_path = None
        self.module = None

    def do_import_from_path(self):
        module_parts = self.import_path.split(".")
        sub_module_name = module_parts[-1]

        hook = hive_editor.get_hook()

        # Find first runtime info object and assume is the only one required
        runtime_infos = self._hive._hive_runtime_info
        if not runtime_infos:
            raise RuntimeError("This hive does not have any runtime info objects (not a child of a hive)")

        first_runtime_info = set(runtime_infos).pop()
        parent = first_runtime_info.parent()
        container_parent_class = parent._hive_object._hive_parent_class

        try:
            directory = os.path.dirname(hook.get_path_of_class(container_parent_class))

        except ValueError:
            context = _no_context

        else:
            context = hook.temporary_relative_context(directory)

        with context:
            module = __import__(self.import_path, fromlist=[sub_module_name])

        self.module = module


def build_import(cls, i, ex, args):
    """Interface to python import mechanism, with respect to editor project path"""
    i.import_path = hive.property(cls, "import_path", 'str')
    i.pull_import_path = hive.pull_in(i.import_path)
    ex.import_path = hive.antenna(i.pull_import_path)

    i.do_import = hive.triggerable(cls.do_import_from_path)

    i.module = hive.property(cls, "module", "module")
    i.pull_module = hive.pull_out(i.module)
    ex.module = hive.output(i.pull_module)

    hive.trigger(i.pull_module, i.pull_import_path, pretrigger=True)
    hive.trigger(i.pull_module, i.do_import, pretrigger=True)


Import = hive.hive("Import", build_import, cls=ImportClass)

