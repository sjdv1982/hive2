from socket import AF_INET, SOCK_STREAM, socket
from socketserver import ThreadingTCPServer, BaseRequestHandler
from threading import Thread


class DebugHandler(BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        print("{} wrote:".format(self.client_address[0]))
        print(self.data)
        # just send back the same data, but upper-cased
        self.request.sendall(self.data.upper())


class Server:

    default_host = 'localhost'
    default_port = 39995

    def __init__(self, host=None, port=None):
        if host is None:
            host = self.default_host

        if port is None:
            port = self.default_port

        self._address = host, port
        self._thread = Thread(target=self._run_socket)

    def _run_socket(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(self._address)
        sock.listen(True)

        connection, address = sock.accept()

        while True:
            data = connection.recv(1024)
            print(data)

    def launch(self):
        self._thread.start()