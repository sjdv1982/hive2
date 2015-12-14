from .manager import ContextFactory, memoize
from .mixins import Parameter
from .tuple_type import tuple_type


class HiveParameter(Parameter):

    def __init__(self, data_type=None, start_value=Parameter.NoValue, options=None):
        self.data_type = tuple_type(data_type)
        self.start_value = start_value
        self.options = options

        # Validate start value
        if not (start_value is Parameter.NoValue or options is None):
            assert start_value in options

    def __repr__(self):
        return "<Parameter: {}>".format(self.start_value)

    @memoize
    def get_runtime_value(self, run_hive):
        return getattr(run_hive._hive_object._hive_args_frozen, self._hive_parameter_name)


parameter = ContextFactory("hive.parameter", declare_mode_cls=HiveParameter, build_mode_cls=HiveParameter)
