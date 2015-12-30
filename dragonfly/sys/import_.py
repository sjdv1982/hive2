import hive


def do_import_from_path(self):
    module_parts = self._import_path.split(".")
    sub_module_name = module_parts[-1]

    module = __import__(self._import_path, fromlist=[sub_module_name])
    self._module = module


def build_import(i, ex, args):
    """Interface to python import mechanism"""
    i.do_import = hive.modifier(do_import_from_path)

    i.import_path = hive.attribute("str")
    i.pull_import_path = hive.pull_in(i.import_path)
    ex.import_path = hive.antenna(i.pull_import_path)

    i.module = hive.attribute("module")
    i.pull_module = hive.pull_out(i.module)
    ex.module = hive.output(i.pull_module)

    hive.trigger(i.pull_module, i.pull_import_path, pretrigger=True)
    hive.trigger(i.pull_module, i.do_import, pretrigger=True)


Import = hive.hive("Import", build_import)
