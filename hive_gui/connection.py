from hive.tuple_type import types_match


class ConnectionType:
    INVALID = 0
    VALID = 1
    TRIGGER = 2 | VALID


class Connection:

    def __init__(self, output_pin, input_pin, is_trigger):
        self._output_pin = output_pin
        self._input_pin = input_pin

        self._is_trigger = is_trigger

        output_pin.add_connection(self)
        input_pin.add_connection(self)

    def delete(self):
        self._input_pin.remove_connection(self)
        self._output_pin.remove_connection(self)

    @property
    def output_pin(self):
        return self._output_pin

    @property
    def input_pin(self):
        return self._input_pin

    @property
    def is_trigger(self):
        return self._is_trigger

    @staticmethod
    def is_valid_between(source, target):
        # If source has no mode
        if source.mode == "any":
            # At least one pin must have unique mode
            if target.mode == "any":
                return ConnectionType.INVALID

        # Both are moded pins
        elif not target.mode == "any":
            # Modes don't match
            if target.mode != source.mode:
                return ConnectionType.INVALID

        # Can't connect two proxy pins together (don't support connect interface)
        if source.is_virtual and target.is_virtual:
            return ConnectionType.INVALID

        # Output pin triggers input BY push
        if not source.is_trigger:
            if source.mode == "push" and target.is_trigger:
                return ConnectionType.TRIGGER

        # Output pin triggers input pin TO pull
        elif target.mode == "pull":
            return ConnectionType.TRIGGER

        # Ask each pin to validate connection
        if not source.can_connect_to(target, is_source=True):
            return ConnectionType.INVALID

        if not target.can_connect_to(source, is_source=False):
            return ConnectionType.INVALID

        if not types_match(source.data_type, target.data_type, allow_none=True):
            return ConnectionType.INVALID

        # If valid connection
        if source.is_trigger and target.is_trigger:
            return ConnectionType.TRIGGER

        return ConnectionType.VALID