from .qt_core import *
from .qt_gui import *
from ..debugging import RemoteDebugServer


class QtRemoteDebugServer(RemoteDebugServer):

    def _on_received(self, data):
        callback = super()._on_received
        event = DeferredExecute(callback, data)
        event.dispatch()


class _Processor(QObject):

    def customEvent(self, e):
        e.process()


class DeferredExecute(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    __processor = _Processor()

    def __init__(self, func, *args, **kwargs):
        QEvent.__init__(self, self.EVENT_TYPE)

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def dispatch(self):
        QApplication.postEvent(self.__processor, self)

    def process(self):
        self.func(*self.args, **self.kwargs)


# TODO DEBUG
# When connection is updated, make bold (width(10)
# Make breakpoint text red
# During debugging session, lock canvas(?) but allow debug features?

# Detail iteration 2
# Overwite hive.connect and hive.trigger / make them poll a debug context?
# Invoke builder with a wrapper:
# def _builder(i, ex, args):
#     with debug_context(hive_map_path): - won't work because UGH