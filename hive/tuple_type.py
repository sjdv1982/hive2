def _check_tuple_type(value):
    if isinstance(value, str):
        return

    assert isinstance(value, tuple), value
    for entry in value:
        _check_tuple_type(entry)


def tuple_type(value):
    if value is None:
        return ()

    if isinstance(value, str):
        return (value,)
    
    _check_tuple_type(value)
    return value


def types_match(data_type_a, data_type_b):
    """Checks that two data type tuples match by comparing their first N elements,
    where N is the length of the shortest data type tuple
    Returns a TypeError otherwise

    :param data_type_a: tuple type of first item
    :param data_type_b: tuple type of second item
    """
    assert isinstance(data_type_a, tuple), data_type_a
    assert isinstance(data_type_b, tuple), data_type_b

    for type_a, type_b in zip(data_type_a, data_type_b):
        if type_a != type_b:
            return False

    return True