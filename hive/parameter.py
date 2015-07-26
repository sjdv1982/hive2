from .mixins import Antenna, Exportable
from .manager import get_building_hive, ContextFactory


class Parameter:

    def __init__(self, data_type=None, start_value=None):
        self.data_type = data_type
        self.start_value = start_value


parameter = ContextFactory("hive.parameter", declare_mode_cls=Parameter)
