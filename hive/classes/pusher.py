class Pusher(object):

    def __init__(self, parent):
        self._parent = parent
        self._targets = []

    def add_target(self, func, name=None):
        assert callable(func)

        pair = name, func
        assert pair not in self._targets, (name, self._parent)
        self._targets.append(pair)

    def push(self, *args, **kwargs):
        for name, func in self._targets:
            # TODO: exception handling
            func(*args, **kwargs)
