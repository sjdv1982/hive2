from PySide.QtGui import *
from PySide.QtCore import *

from functools import partial

from ..utils import Colour, Vector


INT_RANGE = -999, 999
FLOAT_RANGE = -999.0, 999.0
FLOAT_STEP = 0.1


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
        try:
            self.setter(value)

        except Exception as err:
            print("Unable to set value {}: {}".format(value, err))


def _create_str(use_text_area):
    if use_text_area:
        widget = QTextEdit()

        getter = widget.toPlainText
        setter = lambda value: widget.setPlainText(value)

    else:
        widget = QLineEdit()

        getter = widget.text
        setter = lambda value: widget.setText(value)

    controller = WidgetController(getter, setter)

    def on_changed(value=None):
        controller._on_changed(getter())

    widget.textChanged.connect(on_changed)
    controller.__on_changed = on_changed

    return widget, controller


def _create_int(use_text_area):
    widget = QSpinBox()

    widget.setRange(*INT_RANGE)

    getter = widget.value
    setter = lambda value: widget.setValue(value)

    controller = WidgetController(getter, setter)
    widget.valueChanged.connect(controller._on_changed)

    return widget, controller


def _create_float(use_text_area):
    widget = QDoubleSpinBox()

    widget.setRange(*FLOAT_RANGE)
    widget.setSingleStep(FLOAT_STEP)

    getter = widget.value
    setter = lambda value: widget.setValue(value)

    controller = WidgetController(getter, setter)
    widget.valueChanged.connect(controller._on_changed)

    return widget, controller


def _create_bool(use_text_area):
    widget = QCheckBox()

    getter = lambda: bool(widget.isChecked())
    setter = lambda value: widget.setChecked(value)

    controller = WidgetController(getter, setter)

    def on_changed(value=None):
        controller._on_changed(getter())

    widget.stateChanged.connect(on_changed)
    controller.__on_changed = on_changed

    return widget, controller


def _create_vector(use_text_area):
    widget = QWidget()

    layout = QHBoxLayout()
    layout.setSpacing(0.0)

    widget.setLayout(layout)

    # When an individual field is modified
    def field_changed(i, field_value):
        controller._on_changed(getter())

    for i in range(3):
        field = QDoubleSpinBox()

        field.setRange(*FLOAT_RANGE)
        field.setSingleStep(FLOAT_STEP)
        field.valueChanged.connect(partial(field_changed, i))

        layout.addWidget(field)

    def setter(value):
        for i, field_value in enumerate(value):
            field = layout.itemAt(i).widget()
            field.setValue(field_value)

    def getter():
        data = tuple(layout.itemAt(i).widget().value() for i in range(3))
        return Vector(*data)

    controller = WidgetController(getter, setter)
    return widget, controller


def _create_colour(use_text_area):
    widget = QWidget()

    layout = QHBoxLayout()
    layout.setSpacing(0.0)

    widget.setLayout(layout)

    # When an individual field is modified
    def field_changed(i, field_value):
        controller._on_changed(getter())

    for i in range(3):
        field = QDoubleSpinBox()

        field.setRange(*FLOAT_RANGE)
        field.setSingleStep(FLOAT_STEP)
        field.valueChanged.connect(partial(field_changed, i))

        layout.addWidget(field)

    def setter(value):
        for i, field_value in enumerate(value):
            field = layout.itemAt(i).widget()
            field.setValue(field_value)

    def getter():
        data = tuple(layout.itemAt(i).widget().value() for i in range(3))
        return Colour(*data)

    controller = WidgetController(getter, setter)
    return widget, controller


def _create_repr():
    widget = QLineEdit()

    getter = lambda: eval(widget.text())
    setter = lambda value: widget.setText(repr(value))

    controller = WidgetController(getter, setter)
    widget.textChanged.connect(controller._on_changed)

    controller.value = None
    return widget, controller


def _create_options(options):
    widget = QComboBox()
    for i, option in enumerate(options):
        widget.insertItem(i, str(option), option)

    getter = lambda: widget.itemData(widget.currentIndex())
    setter = lambda value: widget.setCurrentIndex(widget.findData(value))

    controller = WidgetController(getter, setter)
    widget.activated.connect(controller._on_changed)
    return widget, controller


_factories = dict(str=_create_str, int=_create_int, float=_create_float, bool=_create_bool, vector=_create_vector,
                  colour=_create_colour)


def create_widget(type_name=None, options=None, use_text_area=False):
    if options is not None:
        return _create_options(options)

    try:
        return _factories[type_name](use_text_area)

    except KeyError:
        return _create_repr()
