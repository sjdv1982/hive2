from collections import OrderedDict
from functools import partial

from hive import types_match
from .colour_button import QColorButton
from .qt_gui import QSpinBox, QLineEdit, QDoubleSpinBox, QTextEdit, QFont, QWidget, QHBoxLayout, QCheckBox, QComboBox, \
    QColor

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


def _create_str():
    widget = QLineEdit()

    getter = widget.text
    setter = lambda value: widget.setText(value)

    controller = WidgetController(getter, setter)

    def on_changed(value=None):
        controller._on_changed(getter())

    widget.textChanged.connect(on_changed)
    controller.__on_changed = on_changed

    return widget, controller


def _create_code():
    widget = QTextEdit()
    widget.setCurrentFont(QFont("Consolas"))

    getter = widget.toPlainText
    setter = lambda value: widget.setPlainText(value)

    controller = WidgetController(getter, setter)

    def on_changed(value=None):
        controller._on_changed(getter())

    widget.textChanged.connect(on_changed)
    controller.__on_changed = on_changed

    return widget, controller


def _create_int():
    widget = QSpinBox()

    widget.setRange(*INT_RANGE)

    getter = widget.value
    setter = lambda value: widget.setValue(value)

    controller = WidgetController(getter, setter)
    widget.valueChanged.connect(controller._on_changed)

    return widget, controller


def _create_float():
    widget = QDoubleSpinBox()

    widget.setRange(*FLOAT_RANGE)
    widget.setSingleStep(FLOAT_STEP)

    getter = widget.value
    setter = lambda value: widget.setValue(value)

    controller = WidgetController(getter, setter)
    widget.valueChanged.connect(controller._on_changed)

    return widget, controller


def _create_bool():
    widget = QCheckBox()

    getter = lambda: bool(widget.isChecked())
    setter = lambda value: widget.setChecked(value)

    controller = WidgetController(getter, setter)

    def on_changed(value=None):
        controller._on_changed(getter())

    widget.stateChanged.connect(on_changed)
    controller.__on_changed = on_changed

    return widget, controller


def _create_vector():
    widget = QWidget()

    layout = QHBoxLayout()
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
        return tuple(layout.itemAt(i).widget().value() for i in range(3))

    controller = WidgetController(getter, setter)

    return widget, controller


def _create_colour():
    """Create a colour widget to display a restricted set of options

    :param options: permitted option values
    """
    widget = QColorButton()

    layout = QHBoxLayout()
    layout.setSpacing(0.0)

    widget.setLayout(layout)

    def setter(colour_rgb):
        colour = QColor.fromRgb(*colour_rgb)
        widget.setColor(colour)

    def getter():
        return tuple(widget.color().getRgb())

    controller = WidgetController(getter, setter)

    def on_changed():
        controller._on_changed(getter())

    widget.colorChanged.connect(on_changed)

    return widget, controller


def _create_repr():
    """Create a UI widget to edit a repr-able value"""
    widget = QLineEdit()

    getter = lambda: eval(widget.text())
    setter = lambda value: widget.setText(repr(value))

    controller = WidgetController(getter, setter)
    widget.textChanged.connect(controller._on_changed)

    controller.value = None
    return widget, controller


def _create_options(options):
    """Create a UI combo widget to display a restricted set of options

    :param options: permitted option values
    """
    widget = QComboBox()

    for i, option in enumerate(options):
        widget.insertItem(i, str(option), option)

    getter = lambda: widget.itemData(widget.currentIndex())
    setter = lambda value: widget.setCurrentIndex(widget.findData(value))

    controller = WidgetController(getter, setter)
    widget.activated.connect(controller._on_changed)
    return widget, controller


_factories = OrderedDict((
    (("str", "code"), _create_code),
    (("str",), _create_str),
    (("int",), _create_int),
    (("float",), _create_float),
    (("bool",), _create_bool),
    (("vector",), _create_vector),
    (("colour",), _create_colour)
    ))


def create_widget(data_type=(), options=None):
    """Create a UI widget to edit a specific value

    :param data_type: data type of value
    :param options: restrict values to a fixed option set
    """
    if options is not None:
        return _create_options(options)

    for factory_type, factory in _factories.items():
        # Don't match str types with (str, code)!
        if len(data_type) < len(factory_type):
            continue

        if types_match(factory_type, data_type, allow_none=False):
            return factory()

    return _create_repr()
