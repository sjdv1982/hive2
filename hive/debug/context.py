from contextlib import contextmanager

_debug_context = None


def get_debug_context():
    return _debug_context


def set_debug_context(context):
    global _debug_context
    _debug_context = context


@contextmanager
def debug_context_as(context):
    original_context = get_debug_context()
    set_debug_context(context)
    yield
    set_debug_context(original_context)


class DebugContextBase:

    def build_connection(self, source, target):
        raise NotImplementedError

    def build_trigger(self, source, target, pre):
        raise NotImplementedError
