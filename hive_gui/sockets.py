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


def get_colour(data_type):
    """Return the appropriate socket colour for data type"""
    if data_type:
        base_type = data_type[0]

        if base_type == "object":
            return colours[0]

        elif base_type == "trigger":
            return colours[1]

        elif base_type == "id":
            return colours[2]

        elif base_type == "str":
            return colours[3]

        elif base_type == "int":
            return colours[4]

        elif base_type == "float":
            return colours[5]

        elif base_type == "bool":
            return colours[6]

        elif base_type == "vector":
            return colours[7]

        elif base_type == "matrix":
            return colours[8]

        elif base_type == "colour":
            return colours[9]

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

