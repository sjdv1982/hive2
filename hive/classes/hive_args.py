from ..mixins import Parameter
from ..six import next


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

    def __repr__(self):
        member_pairs = ("{} = {}".format(k, v) for k, v in self._args.items())
        return "<FrozenHiveArgs (args)>\n\t{}".format("\n\t".join(member_pairs))


class HiveArgs(object):

    def __init__(self, hive_cls):
        self._args = {}
        self._hive_object_cls = hive_cls

        # Use ordered list for arguments (when resolving)
        self._arg_names = []

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

        if name in self._args:
            self._arg_names.remove(name)

        self._args[name] = value
        object.__setattr__(self, name, value)

        self._arg_names.append(name)

    def __getattr__(self, name):
        raise AttributeError("HiveArgs (args) attribute has no attribute '%s'" % name)

    def __delattr__(self, name):
        if name not in self._args:
            raise AttributeError("HiveArgs (args) attribute has no attribute '%s'" % name)

        self._args.pop(name)
        self._arg_names.remove(name)
        object.__delattr__(self, name)

    def __dir__(self):
        return self._arg_names

    def __iter__(self):
        return iter(self._arg_names)

    def __repr__(self):
        member_pairs = ("{} = {}".format(k, v) for k, v in self._args.items())
        return "<HiveArgs (args)>\n\t{}".format("\n\t".join(member_pairs))

    def freeze(self, parameter_values):
        """Resolve all parameter values with their parameter objects and return FrozenHiveArgs view

        :param parameter_values: parameter values returned from extract_parameter_values
        """
        param_pairs = []

        for param_name, parameter_value in zip(self._arg_names, parameter_values):
            parameter = self._args[param_name]

            param_pairs.append((param_name, parameter.resolve(parameter_value)))

        resolved_args = dict(param_pairs)
        return FrozenHiveArgs(resolved_args)

    def extract_parameter_values(self, args, kwargs):
        """Extract parameter values from arguments and keyword arguments provided to the building hive.

        Return the new args and kwargs wrappers, and a tuple of all parameter values

        :param args: tuple of argument values
        :param kwargs: dict of keyword name value pairs
        """
        iter_args = iter(args)
        out_kwargs = kwargs.copy()

        parameter_values = []

        use_args = True
        for param_name in self._arg_names:
            # If param name in kwargs dict, switch to kwargs
            if param_name in out_kwargs:
                use_args = False

                # Pop value from kwargs
                arg_value = out_kwargs.pop(param_name)

            # If not in kwargs and we're using kwargs, break
            else:
                # Provide default None value
                if not use_args:
                    arg_value = None

                else:
                    # Try and take value from args
                    arg_value = next(iter_args, None)

            parameter_values.append(arg_value)

        out_args = tuple(iter_args)
        out_parameter_values = tuple(parameter_values)

        return out_args, out_kwargs, out_parameter_values