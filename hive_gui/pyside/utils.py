from PySide.QtGui import *


def create_widget(data_type, value=None):
    base_type, *_ = data_type

    if base_type == "str":
        widget = QLineEdit()
        if value is not None:
            widget.setText(value)

    elif base_type == "int":
        widget = QSpinBox()
        if value is not None:
            widget.setValue(value)

    elif base_type == "float":
        widget = QDoubleSpinBox()
        if value is not None:
            widget.setValue(value)

    elif base_type == "bool":
        widget = QCheckBox()
        if value is not None:
            widget.setCheckState(value)

    else:
        raise TypeError(data_type)

    return widget