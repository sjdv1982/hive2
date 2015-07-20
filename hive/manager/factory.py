from .contexts import get_mode


class ContextFactory:
    """Return appropriate class instance depending upon execution mode"""

    def __init__(self, name, immediate_cls=None, deferred_cls=None):
        self.name = name
        self.immediate_cls = immediate_cls
        self.deferred_cls = deferred_cls

    def __call__(self, *args, **kwargs):
        mode = get_mode()

        if mode == "immediate":
            cls = self.immediate_cls

        else:
            cls = self.deferred_cls

        if cls is None:
            raise TypeError("{} cannot be used in {} mode".format(self.name, mode))

        return cls(*args, **kwargs)