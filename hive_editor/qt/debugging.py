from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtWidgets import QApplication

from ..debugging.network import NetworkDebugManager


class QtNetworkDebugManager(NetworkDebugManager):

    def _on_connected(self):
        callback = super(QtNetworkDebugManager, self)._on_connected
        event = DeferredExecute(callback)
        event.dispatch()

    def _on_disconnected(self):
        callback = super(QtNetworkDebugManager, self)._on_disconnected
        event = DeferredExecute(callback)
        event.dispatch()

    def _on_received(self, data):
        callback = super(QtNetworkDebugManager, self)._on_received
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
