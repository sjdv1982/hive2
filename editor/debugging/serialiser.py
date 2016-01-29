from struct import pack, unpack_from, calcsize


class Serialiser:

    class OpCodes:
        push_out = 0
        pull_in = 1

    def serialise_operation(self, op_code, ):
        pass

    def deserialise_operation(self):
        pass


class ServerDebugManager:

    def __init__(self):
        self._id_to_bee_name = {}
        self._