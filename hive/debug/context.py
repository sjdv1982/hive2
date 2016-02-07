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


class DebugContextBase(object):

    def build_connection(self, source, target):
        target._hive_connect_target(source)
        source._hive_connect_source(target)

    def build_trigger(self, source, target, pre):
        target_func = target._hive_trigger_target()
        if pre:
            source._hive_pretrigger_source(target_func)

        else:
            source._hive_trigger_source(target_func)
