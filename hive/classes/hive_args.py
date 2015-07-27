from ..mixins import Parameter


class FrozenHiveArgs(object):

    def __init__(self, args):
        self.__dict__.update(args)
        self._args = args

    def __getattr_(self, name):
        raise AttributeError("FrozenHiveArgs (args) has no attribute '%s'" % name)

    def __delattr_(self, name):
        raise AttributeError("FrozenHiveArgs (args) cannot be assigned to")

    def __setattr__(self, name, value):
        if name == "_args":
            object.__setattr__(self, name, value)

        else:
            raise AttributeError("FrozenHiveArgs (args) cannot be assigned to")

    def __dir__(self):
        return self._args.keys()

    def __iter__(self):
        return iter(self._args.keys())


class HiveArgs(object):

    def __init__(self, hive_cls):
        self._args = {}
        self._hive_object_cls = hive_cls

    def __setattr__(self, name, value):
        if name == "parent":
            raise AttributeError("HiveArgs (args) special attribute 'parent' cannot be assigned to" % value.__class__)

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        if value is None:
            if name in self._args:
                self._args.pop(name)

        if not isinstance(value, Parameter):
            raise TypeError("HiveArgs (args) attribute '%s' must be a Parameter, not '%s'" % (name, value.__class__))

        value._hive_parameter_name = name

        self._args[name] = value
        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        raise AttributeError("HiveArgs (args) attribute has no attribute '%s'" % name)

    def __delattr__(self, name):
        if name not in self._args:
            raise AttributeError("HiveArgs (args) attribute has no attribute '%s'" % name)

        self._bee_names.remove(name)
        object.__delattr__(self, name)

    def __dir__(self):
        return self._args.keys()

    def __iter__(self):
        return iter(self._args.keys())

    def freeze(self, kwargs):
        args = {k: v.resolve(kwargs) for k, v in self._args.items()}
        return FrozenHiveArgs(args)