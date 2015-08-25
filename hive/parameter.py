from .mixins import Parameter
from .manager import ContextFactory
from .tuple_type import tuple_type


class HiveParameter(Parameter):

    def __init__(self, data_type=None, start_value=None, options=None):
        self.data_type = tuple_type(data_type)
        self.start_value = start_value
        self.options = options

        # Validate start value
        if options is not None:
            assert start_value in options

    def __repr__(self):
        return "<Parameter: {}>".format(self.start_value)

    def resolve(self, value):
        if value is None:
            value = self.start_value

        # Validate option
        if self.options is not None and value not in self.options:
            raise ValueError("{} is not a permitted value: {}".format(repr(value), self.options))

        return value


parameter = ContextFactory("hive.parameter", declare_mode_cls=HiveParameter)
