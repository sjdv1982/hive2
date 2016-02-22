from contextlib import contextmanager

_debug_context = None


def get_current_context():
    return _debug_context


def set_current_context(context):
    global _debug_context
    _debug_context = context


@contextmanager
def current_context_as(context):
    original_context = get_current_context()
    set_current_context(context)
    yield
    set_current_context(original_context)


class DebugContextBase:

    def build_connection(self, source, target):
        raise NotImplementedError

    def build_trigger(self, source, target, pre):
        raise NotImplementedError
