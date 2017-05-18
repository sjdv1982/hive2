from enum import auto, Enum


class ContextAdaptor:
    """Adaptor to provide interface to context manager"""

    class CtxState(Enum):
        null = auto()
        inside = auto()
        outside = auto()

    def __init__(self, context_mgr):
        self._context_mgr = context_mgr
        self._state = self.CtxState.null

    def __del__(self):
        self.destroyed()

    def destroyed(self):
        print("Context destroyed")
        if self._state == self.CtxState.inside:
            self.exit()

    def enter(self):
        if self._state != self.CtxState.null:
            raise RuntimeError("Context already entered")

        self._state = self.CtxState.inside
        self._context_mgr.__enter__()

    def exit(self):
        if self._state != self.CtxState.inside:
            raise RuntimeError("Context invalid")

        self._state = self.CtxState.outside
        self._context_mgr.__exit__(None, None, None)