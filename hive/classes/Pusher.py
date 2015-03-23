class Pusher(object):

    def __init__(self, parent):
        self._parent = parent
        self._targets = []

    def add_target(self, targetfunc, targetname=None):
        assert callable(targetfunc)
        assert targetname not in self._targets, (targetname, self._parent)
        self._targets.append((targetname, targetfunc))

    def push(self, *args, **kwargs):
        for tname, tfunc in self._targets: 
            #TODO: exception handling
            tfunc(*args, **kwargs)
