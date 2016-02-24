from errno import ECONNRESET, ENODATA
from queue import Queue, Empty
from socket import AF_INET, SOCK_STREAM, socket, error as SOCK_ERROR, SHUT_RDWR, SOL_SOCKET, SO_REUSEADDR
from struct import pack, unpack_from, calcsize
from threading import Event, Thread


class ConnectionBase:

    def __init__(self):
        self._send_queue = Queue()

        self.on_received = None
        self.on_connected = None
        self.on_disconnected = None

        self._received_raw = b''
        self._thread = None

        self._is_running_event = Event()

    def _on_received(self, data):
        self._received_raw += data

        messages = []
        while self._received_raw:
            length, = unpack_from("H", self._received_raw)
            offset = calcsize("H")

            end_index = offset + length
            if end_index > len(self._received_raw):
                break

            message = self._received_raw[offset: end_index]
            self._received_raw = self._received_raw[end_index:]

            messages.append(message)

        if callable(self.on_received):
            for message in messages:
                self.on_received(message)

    def send(self, data):
        length_encoded = pack("H", len(data)) + data
        self._send_queue.put(length_encoded)

    def _run_threaded(self):
        raise NotImplementedError

    def _run_socket_threaded(self, sock, *alive_flags, connected_flag=None):
        if connected_flag is None:
            connected_flag = alive_flags[0]

        send_queue = self._send_queue

        if callable(self.on_connected):
            self.on_connected()

        while all(f.is_set() for f in alive_flags):
            while True:
                try:
                    data = send_queue.get_nowait()

                except Empty:
                    break

                sock.sendall(data)

            while True:
                try:
                    data = sock.recv(1024)

                except OSError as err:
                    if err.errno == ECONNRESET:
                        connected_flag.clear()

                    # Otherwise, timeout failed, just break and allow loop to restart!
                    break

                # Non blocking will only receive no data if lost connection
                if not data:
                    connected_flag.clear()
                    break

                self._on_received(data)

        if callable(self.on_disconnected):
            self.on_disconnected()

        sock.shutdown(SHUT_RDWR)
        sock.close()

    def launch(self, *args, **kwargs):
        self._thread = Thread(target=self._run_threaded, args=args, kwargs=kwargs)
        self._thread.daemon = True

        self._is_running_event.set()
        self._thread.start()

    def stop(self):
        self._is_running_event.clear()
        self._thread.join()


class Client(ConnectionBase):
    default_host = 'localhost'
    default_server_host = 'localhost'
    default_server_port = 39989
    poll_interval = 1 / 200

    def __init__(self, host=None, port=None):
        super(Client, self).__init__()

        if host is None:
            host = self.default_host

        if port is None:
            port = 0

        self._address = host, port

    def _run_threaded(self, server_address=None):
        if server_address is None:
            server_address = self.default_server_host, self.default_server_port

        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(self._address)
        sock.connect(server_address)
        sock.settimeout(self.poll_interval)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        self._is_running_event.set()
        self._run_socket_threaded(sock, self._is_running_event)


class Server(ConnectionBase):
    default_host = 'localhost'
    default_port = 39989
    poll_interval = 1 / 200

    def __init__(self, host=None, port=None):
        super(Server, self).__init__()

        if host is None:
            host = self.default_host

        if port is None:
            port = self.default_port

        self._address = host, port
        self._is_connected_event = Event()

    def disconnect(self):
        self._is_connected_event.clear()

        if callable(self.on_disconnected):
            self.on_disconnected()

    def _run_threaded(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(self._address)
        sock.listen(True)

        while self._is_running_event.is_set():
            connection, address = sock.accept()
            connection.settimeout(self.poll_interval)

            self._is_connected_event.set()
            self._run_socket_threaded(connection, self._is_running_event, self._is_connected_event,
                                      connected_flag=self._is_connected_event)
            self._is_connected_event.clear()

            connection.close()


