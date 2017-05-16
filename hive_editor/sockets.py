import hive


colours = [
    (255, 255, 95),
    (255, 0, 0),
    (0, 255, 0),
    (204, 255, 102),
    (55, 55, 255),
    (5, 207, 146),
    (255, 160, 130),
    (0, 120, 155),
    (0, 120, 155),
    (88, 228, 255),
    (255, 255, 255),
]


base_type_colours = {
    "entity": colours[0],
    "trigger": colours[1],
    "id": colours[2],
    "str": colours[3],
    "bytes": colours[3],
    "int": colours[4],
    "float": colours[5],
    "bool": colours[6],
    "vector": colours[7],
    "matrix": colours[8],
    "colour": colours[9]
}


def get_colour(data_type):
    """Return the appropriate socket colour for data type"""
    as_tuple = hive.identifier_to_tuple(data_type)

    if as_tuple:
        base_type = as_tuple[0]
        try:
            return base_type_colours[base_type]
        except KeyError:
            pass

    return colours[10]


class SocketTypes:
    circle, square, diamond = range(3)


def get_shape(mode):
    if mode == "pull":
        return SocketTypes.square

    elif mode == "push":
        return SocketTypes.circle

    elif mode == "any":
        return SocketTypes.square

    raise ValueError("Invalid mode")

