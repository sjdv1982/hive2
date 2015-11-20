
from ..mixins import Parameter
from .. compatability import next


class FrozenHiveArgs(object):

    def __init__(self, args, name):
        self.__dict__.update(args)

        object.__setattr__(self, "_args", args)
        object.__setattr__(self, "_name", name)

    def __getattr_(self, name):
        raise AttributeError("FrozenHiveArgs ({}) has no attribute '{}'".format(self._name, name))

    def __delattr_(self, name):
        raise AttributeError("FrozenHiveArgs ({}) cannot be assigned to".format(self._name))

    def __setattr__(self, name, value):
        raise AttributeError("FrozenHiveArgs ({}) cannot be assigned to".format(self._name))

    def __bool__(self):
        return bool(self._args)

    def __dir__(self):
        return self._args.keys()

    def __iter__(self):
        return iter(self._args.keys())

    def __repr__(self):
        member_pairs = ("{} = {}".format(k, v) for k, v in self._args.items())
        return "<FrozenHiveArgs ({})>\n\t{}".format(self._name, "\n\t".join(member_pairs))


class HiveArgs(object):

    def __init__(self, hive_cls, name):
        self._hive_object_cls = hive_cls
        self._name = name

        # Use ordered list for arguments (when resolving)
        self._arg_names = []

    def __setattr__(self, name, value):
        if name == "parent":
            raise AttributeError("HiveArgs ({}) special attribute 'parent' cannot be assigned to".format(self._name))

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        if value is None:
            if hasattr(self, name):
                self.__delattr__(name)
            return

        if not isinstance(value, Parameter):
            raise TypeError("HiveArgs ({}) attribute '{}' must be a Parameter, not '{}'"
                            .format(self._name, name, value.__class__))

        value._hive_parameter_name = name

        # Remove and re-add
        if name in self._arg_names:
            self._arg_names.remove(name)

        object.__setattr__(self, name, value)
        self._arg_names.append(name)

    def __getattr__(self, name):
        raise AttributeError("HiveArgs ({}) attribute has no attribute '{}'".format(self._name, name))

    def __delattr__(self, name):
        try:
            object.__delattr__(self, name)

        except AttributeError:
            raise AttributeError("HiveArgs ({}) attribute has no attribute '{}'" .format(self._name, name))

        self._arg_names.remove(name)

    def __bool__(self):
        return bool(self._arg_names)

    def __dir__(self):
        return self._arg_names

    def __iter__(self):
        return iter(self._arg_names)

    def __repr__(self):
        member_pairs = ("{} = {}".format(k, getattr(self, k)) for k in self._arg_names)
        return "<HiveArgs ({})>\n\t{}".format(self._name, "\n\t".join(member_pairs))

    def freeze(self, parameter_values):
        """Resolve all parameter values with their parameter objects and return FrozenHiveArgs view

        :param parameter_values: parameter values returned from extract_parameter_values
        """
        param_pairs = []

        for param_name, parameter_value in zip(self._arg_names, parameter_values):
            parameter = getattr(self, param_name)
            options = parameter.options

            if options is not None and parameter_value not in options:
                raise ValueError("{} is not a permitted value: {}".format(repr(parameter_value), options))

            param_pairs.append((param_name, parameter_value))

        resolved_args = dict(param_pairs)
        return FrozenHiveArgs(resolved_args, self._name)

    def extract_from_args(self, args, kwargs):
        """Extract parameter values from arguments and keyword arguments provided to the building hive.

        Return the new args and kwargs wrappers, and a tuple of all parameter values

        :param args: tuple of argument values
        :param kwargs: dict of keyword name value pairs
        """
        parameter_values = []

        use_args = True
        iter_args = iter(args)
        out_kwargs = kwargs.copy()

        for param_name in self._arg_names:
            parameter = getattr(self, param_name)

            # If param name in kwargs dict, switch to kwargs
            if param_name in out_kwargs:
                use_args = False

                # Pop value from kwargs
                try:
                    arg_value = out_kwargs.pop(param_name)

                except KeyError:
                    # Check if we can omit the value
                    if parameter.start_value is Parameter.NoValue:
                        raise ValueError("No value for '{}' passed to HiveArgs({})"
                                         .format(param_name, self._name))
                    else:
                        arg_value = parameter.start_value
                        print("SET START", param_name, arg_value)

            else:
                # If not in kwargs and we're using kwargs, provide attempt for default
                if not use_args:
                    # Check if we can omit the value
                    if parameter.start_value is Parameter.NoValue:
                        raise ValueError("No value for '{}' passed to HiveArgs({})"
                                         .format(param_name, self._name))
                    else:
                        arg_value = parameter.start_value

                else:
                    # Try and take value from args
                    try:
                        arg_value = next(iter_args)

                    except StopIteration:
                        if parameter.start_value is Parameter.NoValue:
                            raise ValueError("No value for '{}' passed to HiveArgs({})"
                                             .format(param_name, self._name))
                        else:
                            arg_value = parameter.start_value

            parameter_values.append(arg_value)

        out_args = tuple(iter_args)
        out_parameter_values = tuple(parameter_values)

        return out_args, out_kwargs, out_parameter_values