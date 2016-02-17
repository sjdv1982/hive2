from collections import OrderedDict, namedtuple

from . import SPECIAL_NAMES
from .. mixins import Bee, Exportable, Parameter
from .. compatability import next


HiveArgsExtraction = namedtuple("HiveArgsExtraction", "args kwargs parameter_values")


class MappingObject(object):

    def __init__(self):
        self._members = OrderedDict()

    _RESTRICTED_ATTRIBUTES = set()

    @property
    def _CLS_NAME(self):
        return self.__class__.__name__

    def _repr_message(self, message):
        return "{}: {}".format(self._CLS_NAME, message)

    def _validate_attribute(self, name, value):
        pass

    def __setattr__(self, name, value):
        if name in self._RESTRICTED_ATTRIBUTES:
            raise AttributeError(self._repr_message("special attribute '{}' cannot be assigned to".format(name)))

        if name.startswith("_"): 
            return object.__setattr__(self, name, value)

        # Mechanism for deletion of attributes
        if value is None:
            if name in self._members:
                self.__delattr__(name)

            return

        self._validate_attribute(name, value)

        self._members[name] = value
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        try:
            del self._members[name]

        except KeyError:
            raise AttributeError(self._repr_message("no attribute exists with name '{}'".format(name)))

        object.__delattr__(self, name)

    def __bool__(self):
        return bool(self._members)

    def __dir__(self):
        return tuple(self._members)

    def __iter__(self):
        return iter(self._members)

    def __repr__(self):
        member_pairs = ("{} = {}".format(k, v) for k, v in self._members.items())
        return self._repr_message("\n\t{}".format("\n\t".join(member_pairs)))

    @property
    def members(self):
        return self._members.copy()


class HiveObjectWrapper(MappingObject):

    _WRAPPER_NAME = property()

    def __init__(self, hive_object_cls):
        self._hive_object_cls = hive_object_cls

        super(HiveObjectWrapper, self).__init__()

    @property
    def _CLS_NAME(self):
        return "{}.{}".format(self._hive_object_cls.__name__, self._WRAPPER_NAME)


class HiveInternalWrapper(HiveObjectWrapper):

    _RESTRICTED_ATTRIBUTES = SPECIAL_NAMES
    _WRAPPER_NAME = "i"

    def _validate_attribute(self, name, value):
        if not isinstance(value, Bee):
            raise TypeError(self._repr_message("attribute '{}' must be a Bee, not '{}'".format(name, value.__class__)))

        if isinstance(value, Exportable) and value.export_only:
            raise TypeError(self._repr_message("attribute '{}' must not be Exportable; Exportables must be added to ex"
                            .format(name)))

        if value._hive_object_cls is None:
            raise AttributeError(self._repr_message("attribute '{}' must be a Bee instance defined inside the builder"
                                                    "function".format(name)))

        if value._hive_object_cls is not self._hive_object_cls:
            raise AttributeError(self._repr_message("attribute '{}' cannot contain a Bee built by a different hive"
                                                    .format(name)))

        value._hive_wrapper_name = name


class HiveExportableWrapper(HiveObjectWrapper):

    _WRAPPER_NAME = "ex"

    def _validate_attribute(self, name, value):
        if not isinstance(value, Bee):
            raise TypeError(self._repr_message("attribute '{}' must be a Bee, not '{}'".format(name, value.__class__)))

        if not isinstance(value, Exportable):
            raise TypeError(self._repr_message("attribute '{}' must be Exportable; Exportables must be added to ex"
                            .format(name)))

        if value._hive_object_cls is None:
            raise AttributeError(self._repr_message("attribute '{}' must be a Bee instance defined inside the builder"
                                                    "function".format(name)))

        if value._hive_object_cls is not self._hive_object_cls:
            raise AttributeError(self._repr_message("attribute '{}' cannot contain a Bee built by a different hive"
                                                    .format(name)))

        value._hive_wrapper_name = name


class FrozenArgsView(MappingObject):

    def __init__(self, wrapper, frozen_data):
        super(FrozenArgsView, self).__init__()

        self.__dict__.update(frozen_data)
        self._members.update(frozen_data)

        self._wrapper = wrapper

    @property
    def _CLS_NAME(self):
        return "{}[frozen]".format(self._wrapper._CLS_NAME)

    def __delattr_(self, name):
        raise AttributeError(self._repr_message("attributes cannot be removed"))

    def __setattr__(self, name, value):
        if not name.startswith("_"):
            raise AttributeError(self._repr_message("attributes cannot be modified"))

        object.__setattr__(self, name, value)

    def get_parameter_value(self, parameter):
        return self._members[parameter._hive_parameter_name]


class HiveArgsWrapperBase(MappingObject):

    def _validate_attribute(self, name, value):
        if not isinstance(value, Parameter):
            raise TypeError(self._repr_message("attribute '{}' must be a Parameter, not '{}'"
                            .format(name, value.__class__)))

        value._hive_parameter_name = name

    def freeze(self, parameter_values):
        """Resolve all parameter values with their parameter objects and return FrozenHiveArgs view

        :param parameter_values: parameter values returned from extract_parameter_values
        """
        parameter_dict = {}

        for param_name, parameter_value in zip(self._members, parameter_values):
            parameter = self._members[param_name]

            options = parameter.options
            if options is not None and parameter_value not in options:
                raise ValueError("{} is not in the permitted options {} for {}".format(repr(parameter_value), options,
                                                                                       param_name))

            parameter_dict[param_name] = parameter_value

        return FrozenArgsView(self, parameter_dict)

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

        for param_name, parameter in self._members.items():
            # If param name in kwargs dict, switch to kwargs
            if param_name in out_kwargs:
                use_args = False

                # Pop value from kwargs
                try:
                    arg_value = out_kwargs.pop(param_name)

                except KeyError:
                    # Check if we can omit the value
                    if parameter.start_value is Parameter.NoValue:
                        raise ValueError(self._repr_message("No value for '{}' can be resolved".format(param_name)))

                    else:
                        arg_value = parameter.start_value

            else:
                # If not in kwargs and we're using kwargs, provide attempt for default
                if not use_args:
                    # Check if we can omit the value
                    if parameter.start_value is Parameter.NoValue:
                        raise ValueError(self._repr_message("No value for '{}' can be resolved".format(param_name)))
                    else:
                        arg_value = parameter.start_value

                else:
                    # Try and take value from args
                    try:
                        arg_value = next(iter_args)

                    except StopIteration:
                        if parameter.start_value is Parameter.NoValue:
                            raise ValueError(self._repr_message("No value for '{}' can be resolved".format(param_name)))
                        else:
                            arg_value = parameter.start_value

            parameter_values.append(arg_value)

        out_args = tuple(iter_args)
        out_parameter_values = tuple(parameter_values)

        return HiveArgsExtraction(out_args, out_kwargs, out_parameter_values)


class HiveArgsWrapper(HiveObjectWrapper, HiveArgsWrapperBase):

    _WRAPPER_NAME = "args"


class HiveParentWrapper(MappingObject):

    _WRAPPER_NAME = property()

    def __init__(self, hive_parent_cls):
        self._hive_parent_cls = hive_parent_cls

        super(HiveParentWrapper, self).__init__()

    @property
    def _CLS_NAME(self):
        return "{}.{}".format(self._hive_parent_cls.__name__, self._WRAPPER_NAME)


class HiveMetaArgsWrapper(HiveParentWrapper, HiveArgsWrapperBase):

    _WRAPPER_NAME = "meta_args"