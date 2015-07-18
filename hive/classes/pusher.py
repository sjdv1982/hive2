class Pusher(object):

    def __init__(self, parent):
        self._parent = parent
        self._targets = {}

    def add_target(self, func, name=None):
        assert callable(func)
        assert name not in self._targets, (name, self._parent)
        self._targets[name] = func

    def push(self, *args, **kwargs):
        for name, func in self._targets.items():
            # TODO: exception handling
            func(*args, **kwargs)
