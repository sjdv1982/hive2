from queue import Queue, Empty
from socket import AF_INET, SOCK_STREAM, socket, error as SOCK_ERROR
from struct import pack, unpack_from, calcsize
from threading import Lock
from threading import Thread
from weakref import WeakKeyDictionary, ref

from .context import DebugContext
from .utils import get_root_hive, pack_pascal_string
from ..ppout import PushOut


class ConnectionBase:
    default_host = 'localhost'
    default_port = 39989

    def __init__(self, host=None, port=None):
        if host is None:
            host = self.default_host

        if port is None:
            port = self.default_port

        self._address = host, port
        self._send_queue = Queue()

        self.on_received = None

    def send(self, data):
        self._send_queue.put(data)

    def _update_threaded(self):
        raise NotImplementedError

    def launch(self):
        self._thread = Thread(target=self._update_threaded)
        self._thread.start()


class Client(ConnectionBase):

    def _update_threaded(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect(self._address)
        sock.setblocking(False)

        send_queue = self._send_queue
        while True:
            while not send_queue.empty():
                try:
                    data = send_queue.get_nowait()
                except Empty:
                    pass
                else:
                    sock.sendall(data)

            while True:
                try:
                    data = sock.recv(1024)

                except SOCK_ERROR:
                    break

                if callable(self.on_received):
                    self.on_received(data)


class Server(ConnectionBase):

    def _update_threaded(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(self._address)
        sock.listen(True)

        connection, address = sock.accept()

        send_queue = self._send_queue
        while True:
            while not send_queue.empty():
                try:
                    data = send_queue.get_nowait()
                except Empty:
                    pass
                else:
                    connection.sendall(data)

            while True:
                try:
                    data = connection.recv(1024)

                except SOCK_ERROR:
                    break

                if callable(self.on_received):
                    self.on_received(data)


def id_generator(i=0):
    while True:
        yield i
        i += 1


class OpCodes:
    pull_in = 0
    push_out = 1
    trigger = 2

    add_breakpoint = 3
    skip_breakpoint = 4
    remove_breakpoint = 5

    register_root = 6


class DebugPushOutTarget:

    def __init__(self, debug_context, bee_reference):
        self._debug_context = debug_context
        self._bee_reference = bee_reference

    def push(self, value):
        self._debug_context.report_push_out(self._bee_reference(), value)


class RemoteDebugContext(DebugContext):

    def __init__(self):
        self._root_hives = WeakKeyDictionary()
        self._root_hive_ref_to_id = {}

        self._id_generator = id_generator()

        self._client = Client()
        self._client.launch()
        self._client.on_received = self._on_received_response

        self._breakpoints = {}

    def report_trigger(self, source_bee):
        self._report(OpCodes.trigger, source_bee)

    def report_push_out(self, source_bee, data):
        self._report(OpCodes.push_out, source_bee, data)

    def report_pull_in(self, source_bee, data):
        self._report(OpCodes.pull_in, source_bee, data)

    def on_create_connection(self, source, target):
        if isinstance(source, PushOut):
            target = DebugPushOutTarget(self, ref(source))
            source._hive_connect_source(target)

    def on_create_trigger(self, source, target, target_func, pre):
        pass

    def _on_received_response(self, response):
        opcode = unpack_from('B', response)
        remainder = response[calcsize('B'):]

        if opcode == OpCodes.add_breakpoint:
            self._add_breakpoint(remainder)

        elif opcode == OpCodes.remove_breakpoint:
            self._remove_breakpoint(remainder)

        elif opcode == OpCodes.skip_breakpoint:
            self._skip_breakpoint(remainder)

    def _add_breakpoint(self, message):
        root_hive_id, delimited_bee_name = unpack_from('Bp', message)
        bee_name = delimited_bee_name.split(',')

        self._breakpoints[(root_hive_id, bee_name)] = Lock()

    def _remove_breakpoint(self, message):
        root_hive_id, delimited_bee_name = unpack_from('Bp', message)
        bee_name = delimited_bee_name.split(',')

        lock = self._breakpoints.pop((root_hive_id, bee_name))

        try:
            lock.release()

        except RuntimeError:
            pass

    def _skip_breakpoint(self, message):
        root_hive_id, delimited_bee_name = unpack_from('Bp', message)
        bee_name = delimited_bee_name.split(',')

        lock = self._breakpoints[(root_hive_id, bee_name)]

        try:
            lock.release()

        except RuntimeError:
            pass

    def _send_command(self, opcode, data):
        all_data = pack('B', opcode) + data
        self._client.send(all_data)

    def _send_operation(self, opcode, root_hive_id, bee_name, data):
        delimited_bee_name = ','.join(bee_name)

        data = pack('B', root_hive_id) + pack_pascal_string(delimited_bee_name)

        if opcode != OpCodes.trigger:
            data += pack_pascal_string(repr(data))

        self._send_command(opcode, data)

    def _notify_create_root_hive(self, root_hive, root_hive_id):
        raise NotImplementedError

    def _find_root_hive(self, bee):
        return get_root_hive(bee)

    def _report(self, opcode, source_bee, data=None):
        # Memoize root hive
        try:
            root_hive_ref = self._root_hives[source_bee]

        except KeyError:
            root_hive = self._find_root_hive(source_bee)
            # Ignore hive if not permitted
            if root_hive is None:
                return

            root_hive_ref = self._root_hives[source_bee] = ref(root_hive)

        # Memoize root hive identifier
        try:
            root_hive_id = self._root_hive_ref_to_id[root_hive_ref]

        except KeyError:
            root_hive_id = self._root_hive_ref_to_id[root_hive_ref] = next(self._id_generator)
            self._notify_create_root_hive(root_hive_ref(), root_hive_id)

        bee_name = source_bee._hive_bee_name

        # Send operation ...
        self._send_operation(opcode, root_hive_id, bee_name, data)

        # Check for breakpoint on pin
        try:
            breakpoint = self._breakpoints[root_hive_id, bee_name]

        except KeyError:
            pass

        else:
            breakpoint.acquire()
