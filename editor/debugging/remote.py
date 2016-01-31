from queue import Queue, Empty
from socket import AF_INET, SOCK_STREAM, socket, error as SOCK_ERROR
from struct import pack, unpack_from, calcsize
from threading import Lock
from threading import Thread
from weakref import WeakKeyDictionary, ref

from hive.debug.context import DebugContext
from hive.ppout import PushOut

from struct import pack

from functools import lru_cache

from .utils import get_root_hive, pack_pascal_string, unpack_pascal_string
from ..importer import get_hook


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
    register_root, pull_in, push_out, trigger, pretrigger, add_breakpoint, skip_breakpoint, remove_breakpoint = range(8)


class DebugPushOutTarget:

    def __init__(self, debug_context, bee_reference):
        self._debug_context = debug_context
        self._bee_reference = bee_reference

    def push(self, value):
        self._debug_context.report_push_out(self._bee_reference, value)


class DebugTriggerTarget:

    def __init__(self, debug_context, bee_reference):
        self._debug_context = debug_context
        self._bee_reference = bee_reference

    def __call__(self):
        self._debug_context.report_trigger(self._bee_reference)


class DebugPretriggerTarget:

    def __init__(self, debug_context, bee_reference):
        self._debug_context = debug_context
        self._bee_reference = bee_reference

    def __call__(self):
        self._debug_context.report_pretrigger(self._bee_reference)


class RemoteDebugContext(DebugContext):

    def __init__(self):
        self._container_hives = WeakKeyDictionary()
        self._container_hive_ref_to_id = {}

        self._id_generator = id_generator()

        self._client = Client()
        self._client.launch()
        self._client.on_received = self._on_received_response

        self._breakpoints = {}

    def report_trigger(self, source_bee_ref):
        self._report(OpCodes.trigger, source_bee_ref)

    def report_pretrigger(self, source_bee_ref):
        self._report(OpCodes.pretrigger, source_bee_ref)

    def report_push_out(self, source_bee_ref, data):
        self._report(OpCodes.push_out, source_bee_ref, data)

    def report_pull_in(self, source_bee_ref, data):
        self._report(OpCodes.pull_in, source_bee_ref, data)

    def on_create_connection(self, source, target):
        if isinstance(source, PushOut):
            target = DebugPushOutTarget(self, ref(source))
            source._hive_connect_source(target)

    def on_create_trigger(self, source, target, target_func, pre):
        if pre:
            callable_target = DebugPretriggerTarget(self, ref(source))
            source._hive_pretrigger_source(callable_target)

        else:
            callable_target = DebugTriggerTarget(self, ref(source))
            source._hive_trigger_source(callable_target)

    def _on_received_response(self, response):
        opcode, = unpack_from('B', response)
        remainder = response[calcsize('B'):]

        if opcode == OpCodes.add_breakpoint:
            self._add_breakpoint(remainder)

        elif opcode == OpCodes.remove_breakpoint:
            self._remove_breakpoint(remainder)

        elif opcode == OpCodes.skip_breakpoint:
            self._skip_breakpoint(remainder)

    def _add_breakpoint(self, message):
        root_hive_id, = unpack_from('B', message)
        bee_container_name = unpack_pascal_string(message, offset=1)

        self._breakpoints[(root_hive_id, bee_container_name)] = Lock()

    def _remove_breakpoint(self, message):
        root_hive_id, = unpack_from('B', message)
        bee_container_name = unpack_pascal_string(message, offset=1)

        lock = self._breakpoints.pop((root_hive_id, bee_container_name))

        try:
            lock.release()

        except RuntimeError:
            pass

    def _skip_breakpoint(self, message):
        root_hive_id, = unpack_from('B', message)
        bee_container_name = unpack_pascal_string(message, offset=1)

        lock = self._breakpoints[(root_hive_id, bee_container_name)]

        try:
            lock.release()

        except RuntimeError:
            pass

    def _send_command(self, opcode, payload):
        serialised = pack('B', opcode) + payload
        self._client.send(serialised)

    def _send_operation(self, opcode, root_hive_id, bee_container_name, data):
        serialised = pack('B', root_hive_id) + pack_pascal_string(bee_container_name)

        if opcode != OpCodes.trigger:
            serialised += pack_pascal_string(repr(data))

        self._send_command(opcode, serialised)

    def _send_container_hive_id(self, root_hive_id, container_hive_path):
        data = pack_pascal_string(container_hive_path) + pack('B', root_hive_id)
        self._send_command(OpCodes.register_root, data)

    @lru_cache()
    def _find_container_hive_path(self, source_bee_ref):
        # Now find last hivemap
        importer = get_hook()
        get_file_path = importer.get_path_of_class

        try:
            containing_hive = source_bee_ref().parent.parent

        except AttributeError:
            raise ValueError("Invalid bee path structure")

        try:
            parent_builder_class = containing_hive._hive_object._hive_parent_class

        except AttributeError:
            raise ValueError("Bee was not a hive object")

        # If this fails, not a hivemap hive
        return get_file_path(parent_builder_class)

    @lru_cache()
    def _get_container_hive_id(self, container_hive_path):
        hive_id = next(self._id_generator)
        self._send_container_hive_id(hive_id, container_hive_path)
        return hive_id

    def _report(self, opcode, source_bee_ref, data=None):
        try:
            container_hive_path = self._find_container_hive_path(source_bee_ref)
        except ValueError:
            return

        container_hive_id = self._get_container_hive_id(container_hive_path)

        # Create a relative name (node_name.antenna/output)
        node_name, bee_name = source_bee_ref()._hive_bee_name[-2:]

        # Assume using i wrapper
        assert node_name[0] == '_'
        node_name = node_name[1:]

        bee_container_name = "{}.{}".format(node_name, bee_name)

        # Send operation ...
        self._send_operation(opcode, container_hive_id, bee_container_name, data)

        # Check for breakpoint on pin
        try:
            breakpoint = self._breakpoints[container_hive_id, bee_container_name]

        except KeyError:
            pass

        else:
            breakpoint.acquire()


class RemoteDebugServer:

    def __init__(self, host=None, port=None):
        self._server = Server(host, port)
        self._server.on_received = self._on_received

        self._container_id_to_filepath = {}
        self._server.launch()

    def add_breakpoint(self, root_hive_id, bee_name):
        pass

    def _on_received(self, data):
        self._process_data(data)

    def _on_received_push_out(self, root_id, bee_name, value):
        pass

    def _on_received_pull_in(self, root_id, bee_name, value):
        pass

    def _on_received_trigger(self, root_id, bee_name):
        pass

    def _on_received_pretrigger(self, root_id, bee_name):
        pass

    def _on_received_register_container_id(self, root_id, file_path):
        self._container_id_to_filepath[root_id] = file_path

    def _process_data(self, data):
        opcode, = unpack_from('B', data)
        offset = 1

        if opcode == OpCodes.register_root:
            file_path, read_bytes = unpack_pascal_string(data, offset=offset)
            offset += read_bytes

            container_id, = unpack_from('B', data, offset=offset)
            offset += 1

            self._on_received_register_container_id(container_id, file_path)

        elif opcode == OpCodes.push_out:
            container_id, = unpack_from('B', data, offset=offset)
            offset += 1

            container_bee_name, read_bytes = unpack_pascal_string(data, offset=offset)
            offset += read_bytes

            value, read_bytes = unpack_pascal_string(data, offset=offset)
            self._on_received_push_out(container_id, container_bee_name, value)

        elif opcode == OpCodes.trigger:
            container_id = unpack_from('B', data, offset=offset)[0]
            offset += 1

            container_bee_name, read_bytes = unpack_pascal_string(data, offset=offset)
            offset += read_bytes

            self._on_received_trigger(container_id, container_bee_name)

        elif opcode == OpCodes.pretrigger:
            container_id = unpack_from('B', data, offset=offset)[0]
            offset += 1

            container_bee_name, read_bytes = unpack_pascal_string(data, offset=offset)
            offset += read_bytes

            self._on_received_pretrigger(container_id, container_bee_name)