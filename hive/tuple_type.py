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