def get_root_hive(bee):
    while getattr(bee, 'parent', None):
        bee = bee.parent

    return bee