from .mixins import Parameter
from .manager import ContextFactory
from .tuple_type import tuple_type


class HiveParameter(Parameter):

    def __init__(self, data_type=None, start_value=None):
        self.data_type = tuple_type(data_type)
        self.start_value = start_value

    def __repr__(self):
        return "<Parameter: {}>".format(self.start_value)

    def resolve(self, value):
        if value is None:
            return self.start_value

        return value


parameter = ContextFactory("hive.parameter", declare_mode_cls=HiveParameter)
