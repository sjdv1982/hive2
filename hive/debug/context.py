from contextlib import contextmanager
from weakref import WeakKeyDictionary, WeakValueDictionary

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


def id_generator(i=0):
    while True:
        yield i
        i += 1


class DebugContext:

    def __init__(self):
        self._hive_to_id = WeakKeyDictionary()
        self._id_to_hive = WeakValueDictionary()

        self._id_generator = id_generator()
        self.on_reported = None

    def add_hive(self, run_hive):
        if run_hive in self._hive_to_id:
            return

        hive_id = next(self._id_generator)

        self._hive_to_id[run_hive] = hive_id
        self._id_to_hive[hive_id] = run_hive

    def report(self, operation, source_bee, data=None):
        if not callable(self.on_reported):
            return

        bee_hive = source_bee.parent
        bee_parent_id = self._hive_to_id[bee_hive]
        bee_name = source_bee._hive_bee_name

        self.on_reported(operation, bee_parent_id, bee_name, data)