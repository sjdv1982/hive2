def identifier_is_valid(value):
    if isinstance(value, str):
        return True

    if not isinstance(value, tuple):
        return False

    return all((isinstance(x, str) for x in value))


def identifier_to_tuple(value, allow_none=True):
    """Generate a tuple identifier from a string / tuple object.

    String identifiers are split by full-stop '.'.
    """
    if value is None:
        if not allow_none:
            raise ValueError("None is not permitted!")
        return ()

    if isinstance(value, str):
        return tuple(value.split('.'))
    
    if not identifier_is_valid(value):
        raise ValueError("'{}' is not a valid identifier".format(value))

    return value


def identifiers_match(identifier_a, identifier_b, support_untyped=True):
    """Checks that two identifier strings match by comparing their first N elements,
    where N is the length of the shortest converted data type tuple

    :param identifier_a: string of first identifier
    :param identifier_b: string of second identifier
    """

    if not (identifier_a and identifier_b):
        return support_untyped

    else:
        type_a = identifier_to_tuple(identifier_a)
        type_b = identifier_to_tuple(identifier_b)

        for element_type_a, element_type_b in zip(type_a, type_b):
            if element_type_a != element_type_b:
                return False
    return True


def is_subtype(data_type, base_type):
    base_as_tuple = identifier_to_tuple(base_type)
    type_as_tuple = identifier_to_tuple(data_type)

    if len(type_as_tuple) < len(base_as_tuple):
        return False

    for element_type_a, element_type_b in zip(base_as_tuple, type_as_tuple):
        if element_type_a != element_type_b:
            return False

    return True