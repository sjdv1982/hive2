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

        elif base_type in ("str", "String"):
            return colours[3]

        elif base_type in ("int", "Integer"):
            return colours[4]

        elif base_type in ("float", "Float"):
            return colours[5]

        elif base_type in ("bool", "Bool"):
            return colours[6]

        elif base_type in ("Coordinate", "Vector"):
            return colours[7]

        elif base_type == "AxisSystem":
            return colours[8]

        elif base_type == "Color":
            return colours[9]

    return colours[10]


class SocketTypes:
    circle, square, diamond = range(3)


def get_shape(mode):
    if mode == "pull":
        return SocketTypes.square

    elif mode == "push":
        return SocketTypes.circle

    raise ValueError("Invalid mode")

