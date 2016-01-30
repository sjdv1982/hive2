from struct import pack, unpack_from


def get_root_hive(bee):
    while getattr(bee, 'parent', None):
        bee = bee.parent

    return bee


def pack_pascal_string(string):
    return pack("B{}s".format(len(string)), len(string), string.encode())


def unpack_pascal_string(data, offset=0):
    start_offset = offset
    size = unpack_from('B', data, offset=offset)[0]
    offset += 1
    result = unpack_from("{}s".format(size), data, offset=offset)[0].decode()
    offset += size
    return result, offset - start_offset
