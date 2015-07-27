from .mixins import Parameter
from .manager import ContextFactory


class HiveParameter(Parameter):

    def __init__(self, data_type=None, start_value=None):
        self.data_type = data_type
        self.start_value = start_value

    def __repr__(self):
        return "<Parameter: {}>".format(self.start_value)

    def resolve(self, kwargs):
        return kwargs.get(self._hive_parameter_name, self.start_value)


parameter = ContextFactory("hive.parameter", declare_mode_cls=HiveParameter)
