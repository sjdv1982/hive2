from PySide.QtGui import *
from PySide.QtCore import *


class WidgetController:

    def __init__(self, getter, setter):
        self.on_changed = None
        self.setter = setter
        self.getter = getter

    def _on_changed(self, value):

        if callable(self.on_changed):
            self.on_changed(value)

    @property
    def value(self):
        return self.getter()

    @value.setter
    def value(self, value):
        self.setter(value)


def create_widget(data_type, options=None):
    base_type, *_ = data_type

    if options is not None:
        widget = QComboBox()
        for i, option in enumerate(options):
            widget.insertItem(i, str(option), option)

        getter = lambda: widget.itemData(widget.currentIndex())
        setter = lambda value: widget.setCurrentIndex(widget.findData(value))

        controller = WidgetController(getter, setter)
        widget.activated.connect(controller._on_changed)

    else:
        if base_type == "str":
            widget = QLineEdit()

            getter = widget.text
            setter = lambda value: widget.setText(value)

            controller = WidgetController(getter, setter)
            widget.textChanged.connect(controller._on_changed)

        elif base_type == "int":
            widget = QSpinBox()

            getter = widget.value
            setter = lambda value: widget.setValue(value)

            controller = WidgetController(getter, setter)
            widget.valueChanged.connect(controller._on_changed)

        elif base_type == "float":
            widget = QDoubleSpinBox()

            getter = widget.value
            setter = lambda value: widget.setValue(value)

            controller = WidgetController(getter, setter)
            widget.valueChanged.connect(controller._on_changed)

        elif base_type == "bool":
            widget = QCheckBox()

            getter = widget.isChecked
            setter = lambda value: widget.setChecked(value)

            controller = WidgetController(getter, setter)
            widget.stateChanged.connect(controller._on_changed)

        else:
            widget = QLineEdit()

            getter = lambda: eval(widget.text)
            setter = lambda value: widget.setText(repr(value))

            controller = WidgetController(getter, setter)
            widget.textChanged.connect(controller._on_changed)

    return widget, controller