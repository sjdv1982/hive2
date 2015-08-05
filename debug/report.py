"""Basic debugging encoder for HIVE

Connection information (push, pull, trigger) is pushed onto a stack, where it can later be encoded.
Source and target names are currently used (more bandwidth), but make things simple to debug.
Data is encoded according to the data type provided. If not available, types can be inferred, or finally repr-string used.
"""

from struct import pack, unpack_from, calcsize, Struct

stack = []


class OpCodes:
    push, pull, trigger = range(3)


def report_push(source_name, target, data_type, value):
    stack.append((OpCodes.push, source_name, target, data_type, value))


def report_pull(source_name, target, data_type, value):
    # TODO report pre-pull? Because it will back-track
    stack.append((OpCodes.pull, source_name, target, data_type, value))


def report_trigger(source_name, target):
    stack.append((OpCodes.trigger, source_name, target))


def _decode_string(view):
    count = view[0]
    return view[count + 1:], bytes(view[1:1 + count]).decode()


def _encode_string(value):
    assert len(value) <= 255
    return pack("B" + "c" * len(value), len(value), value.encode("utf-8"))


_int_size = calcsize("i")
_float_size = calcsize("f")
_uint8_packer = Struct("B")


def _encode_value(type_info, value, permit_type_inference=False):
    if type_info:
        data_type = type_info[0]

        if data_type == "int" or data_type == "bool":
            return b'i' + pack("i", value)

        if data_type == "float":
            return b'f' + pack("f", value)

        if data_type == "string":
            result = b's' + pack("B" + "{}s".format(len(value)), len(value), value.encode("utf-8"))

    # For types we don't have info for, use repr for string representation, try eval other side
    else:
        if permit_type_inference:
            if isinstance(value, bool):
                type_info = ("bool",)
            elif isinstance(value, int):
                type_info = ("int",)
            elif isinstance(value, float):
                type_info = ("float",)
            elif isinstance(value, str):
                type_info = ("str",)
            else:
                type_info = ()
                print("Failed to infer type for {}".format(value))

            if type_info:
                return _encode_value(type_info, value, False)

        value_str = repr(value)
        return b'x' + _uint8_packer.pack(len(value_str)) + pack("{}s".format(len(value_str)), value_str.encode("utf-8"))


def _decode_value(view):
    fmt = chr(view[0])
    view = view[1:]

    if fmt == "i":
        value = unpack_from("i", view)[0]
        return view[_int_size:], value

    if fmt == "f":
        value = unpack_from("f", view)[0]
        return view[_float_size:], value

    if fmt == "s":
        chars = view[0]
        view = view[1:]

        value = bytes(view[:chars]).decode()
        return view[chars:], value

    if fmt == "x":
        chars = view[0]
        view = view[1:]

        value_str = bytes(view[:chars]).decode()

        try:
            value = eval(value_str)

        except ValueError:
            print("Failed to eval repr result: {}".format(value_str))
            value = value_str

        return view[chars:], value

    raise ValueError("Invalid FMT char: {}".format(fmt))


# TODO some form of debug context to know which hive we're in, push as single operation, or do it parsing side

def encode_and_clear_stack(permit_type_inference=False):
    output_bytes = bytearray()

    pack_opcode = _uint8_packer.pack

    trigger_opcode = OpCodes.trigger

    for operation in stack:
        opcode, source_name, target_name, *_ = operation

        output_bytes.extend(pack_opcode(opcode))
        output_bytes.extend(_encode_string(source_name))
        output_bytes.extend(_encode_string(target_name))

        if opcode != trigger_opcode:
            output_bytes.extend(_encode_value(*_, permit_type_inference=permit_type_inference))

    stack.clear()
    return output_bytes


def decode_and_fill_stack(data):
    trigger_opcode = OpCodes.trigger

    view = memoryview(data)
    while view:
        opcode = view[0]
        view = view[1:]

        view, source = _decode_string(view)
        view, target = _decode_string(view)

        if opcode != trigger_opcode:
            view, value = _decode_value(view)

            stack.append((opcode, source, target, None, value))

        else:
            stack.append((opcode, source, target, ("trigger",)))