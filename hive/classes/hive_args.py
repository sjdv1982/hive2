class HiveArgument(object):
    def __init__(self, name, hive_args):
        self._hive_args = hive_args
        self.name = name


class HiveArgs(object):

    def __init__(self, hive_cls):
        self._args = {}
        self._hive_cls = hive_cls

    def __setattr__(self, name, value):
        if name == "parent":
            raise AttributeError("HiveArgs (args) special attribute 'parent' cannot be assigned to" % value.__class__)

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        if value is None:
            if name in self._args:
                self._args.pop(name)

        else:
            raise AttributeError("Setting attribute '%s' on HiveArgs (args) object is not allowed" % name)

    def __getattr__(self, name):
        if name.startswith("_"): 
            return object.__getattr__(self, name)

        if name not in self._args:
            self._args[name] = HiveArgument(name, self)

        return self._args[name]