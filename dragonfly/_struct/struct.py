import hive
from struct import pack, unpack_from, calcsize


def declare_struct(meta_args):
    pass


def build_struct(i, ex, args, meta_args):
    pass



Struct = hive.dyna_hive("Struct", build_struct, declarator=declare_struct)