from socket import AF_INET, SOCK_STREAM, socket
from threading import Thread
from queue import Queue


class Client:
    default_host = 'localhost'
    default_port = 39995

    def __init__(self, host=None, port=None):
        if host is None:
            host = self.default_host

        if port is None:
            port = self.default_port

        self._address = host, port
        self._thread = Thread(target=self._run_socket)
        self._queue = Queue()

    def enqueue(self, data):
        self._queue.put(data)

    def _run_socket(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect(self._address)

        queue = self._queue
        while True:
            data = queue.get(True)
            sock.sendall(data)

    def launch(self):
        self._thread.start()