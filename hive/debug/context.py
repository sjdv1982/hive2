_debug_context = None


def get_debug_context():
    return _debug_context


def set_debug_context(context):
    global _debug_context
    if context is not None:
        assert _debug_context is None
    _debug_context = context


class DebugContextBase(object):

    def __enter__(self):
        set_debug_context(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_debug_context(None)

    def build_connection(self, source, target):
        raise NotImplementedError

    def build_trigger(self, source, target, pre):
        raise NotImplementedError
