def _validate_tuple(value):
    if isinstance(value, str):
        return

    assert isinstance(value, tuple), value
    for entry in value:
        _validate_tuple(entry)


def identifier_to_tuple(value, allow_none=True):
    if value is None:
        if not allow_none:
            raise ValueError("None is not permitted!")
        return ()

    if isinstance(value, str):
        return tuple(value.split('.'))
    
    _validate_tuple(value)
    return value


def identifiers_match(identifier_a, identifier_b, allow_none=True):
    """Checks that two identifiertuples match by comparing their first N elements,
    where N is the length of the shortest data type tuple
    Returns a TypeError otherwise

    :param identifier_a: tuple of first identifier
    :param identifier_b: tuple of second identifier
    """
    if not (identifier_a and identifier_b):
        return allow_none

    else:
        for type_a, type_b in zip(identifier_a, identifier_b):
            if type_a != type_b:
                return False

    return True