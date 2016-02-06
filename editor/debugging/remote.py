import os
from collections.abc import KeysView
from errno import ECONNRESET
from functools import lru_cache, partial
from queue import Queue, Empty
from socket import AF_INET, SOCK_STREAM, socket, error as SOCK_ERROR
from struct import pack, unpack_from, calcsize
from threading import Event, Thread
from weakref import WeakKeyDictionary, ref

from hive.debug.context import DebugContext
from hive.ppout import PushOut
from .utils import pack_pascal_string, unpack_pascal_string
from ..importer import get_hook


class ConnectionBase:
    def __init__(self):
        self._send_queue = Queue()

        self.on_received = None
        self.on_connected = None
        self.on_disconnected = None

        self._received_raw = b''

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

    def launch(self, *args, **kwargs):
        self._thread = Thread(target=self._run_threaded, args=args, kwargs=kwargs)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._thread.join()


class Client(ConnectionBase):
    default_host = 'localhost'
    default_server_host = 'localhost'
    default_server_port = 39989
    poll_interval = 1/200
    
    def __init__(self, host=None, port=None):
        super().__init__()

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

        send_queue = self._send_queue

        if callable(self.on_connected):
            self.on_connected()

        while True:
            while True:
                try:
                    data = send_queue.get_nowait()
                except Empty:
                    break

                sock.sendall(data)

            while True:
                try:
                    data = sock.recv(1024)

                except SOCK_ERROR:
                    break

                self._on_received(data)

        if callable(self.on_disconnected):
            self.on_disconnected()


class Server(ConnectionBase):
    default_host = 'localhost'
    default_port = 39989
    poll_interval = 1/200

    def __init__(self, host=None, port=None):
        super().__init__()

        if host is None:
            host = self.default_host

        if port is None:
            port = self.default_port

        self._address = host, port
        self._connected = Event()

    def disconnect(self):
        self._connected.clear()

    def _run_threaded_for_connection(self, connection, address):
        send_queue = self._send_queue

        self._connected.set()

        if callable(self.on_connected):
            self.on_connected()

        while self._connected.is_set():
            while True:
                try:
                    data = send_queue.get_nowait()

                except Empty:
                    break

                connection.sendall(data)

            while True:
                try:
                    data = connection.recv(1024)

                except OSError as err:
                    if err.errno == ECONNRESET:
                        self.disconnect()

                    break

                self._on_received(data)

        if callable(self.on_disconnected):
            self.on_disconnected()

    def _run_threaded(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(self._address)
        sock.listen(True)

        while True:
            connection, address = sock.accept()
            connection.settimeout(self.poll_interval)

            self._run_threaded_for_connection(connection, address)

            connection.close()


def id_generator(i=0):
    while True:
        yield i
        i += 1


class OpCodes:
    (register_root, pull_in, push_out, trigger,
     pretrigger, add_breakpoint, skip_breakpoint,
     remove_breakpoint, hit_breakpoint) = range(9)


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
        self._client.on_disconnected = self._on_disconnected

        self._breakpoints = {}

    def _clear_breakpoints(self):
        for breakpoint in self._breakpoints.values():
            self._unset_breakpoint(breakpoint)

        self._breakpoints()

    def _on_disconnected(self):
        self._clear_breakpoints()

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
        body = response[calcsize('B'):]

        if opcode == OpCodes.add_breakpoint:
            self._add_breakpoint(body)

        elif opcode == OpCodes.remove_breakpoint:
            self._remove_breakpoint(body)

        elif opcode == OpCodes.skip_breakpoint:
            self._skip_breakpoint(body)

        else:
            raise ValueError("Invalid OPCODE: '{}'".format(opcode))

    def _add_breakpoint(self, message):
        root_hive_id, = unpack_from('B', message)
        bee_container_name, read_bytes = unpack_pascal_string(message, 1)

        print("DBG::Add breakpoint!", [bee_container_name])
        self._breakpoints[(root_hive_id, bee_container_name)] = Event()

    def _remove_breakpoint(self, message):
        root_hive_id, = unpack_from('B', message)
        bee_container_name, read_bytes = unpack_pascal_string(message, 1)
        print("DBG::Remove breakpoint!", [bee_container_name])

        breakpoint = self._breakpoints.pop((root_hive_id, bee_container_name))
        self._unset_breakpoint(breakpoint)

    def _skip_breakpoint(self, message):
        root_hive_id, = unpack_from('B', message)
        bee_container_name, read_bytes = unpack_pascal_string(message, 1)

        breakpoint = self._breakpoints[(root_hive_id, bee_container_name)]
        print("DBG::Skip breakpoint!", bee_container_name)
        self._unset_breakpoint(breakpoint)

    def _unset_breakpoint(self, breakpoint):
        try:
            breakpoint.set()
            breakpoint.clear()

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
        bee_name = bee_name.lstrip('_')

        bee_container_name = "{}.{}".format(node_name, bee_name)
        print("DBG::Report", bee_container_name, opcode)

        # Send operation ...
        self._send_operation(opcode, container_hive_id, bee_container_name, data)

        # Check for breakpoint on pin
        try:
            breakpoint = self._breakpoints[container_hive_id, bee_container_name]

        except KeyError:
            return

        file_name = os.path.basename(container_hive_path)
        print("Hit breakpoint @ {} - {}".format(file_name, bee_container_name))
        breakpoint.wait()


class HivemapDebugController:

    def __init__(self, file_path):
        self._breakpoints = set()
        self._file_path = file_path

        self.on_push_out = None
        self.on_pull_in = None
        self.on_trigger = None
        self.on_pretrigger = None
        self.on_breakpoint_hit = None
        self.on_io = None

        self._request_close = None

    @property
    def breakpoints(self):
        return KeysView(self._breakpoints)

    @property
    def file_path(self):
        return self._file_path

    def close(self):
        self._request_close()

    def on_closed(self):
        pass

    def add_breakpoint(self, bee_name):
        assert bee_name not in self._breakpoints
        self._breakpoints.add(bee_name)

        data = pack_pascal_string(bee_name)
        self.send_operation(OpCodes.add_breakpoint, data)

    def remove_breakpoint(self, bee_name):
        self._breakpoints.remove(bee_name)
        data = pack_pascal_string(bee_name)

        self.send_operation(OpCodes.remove_breakpoint, data)

    def skip_breakpoint(self, bee_name):
        if bee_name not in self._breakpoints:
            raise ValueError

        data = pack_pascal_string(bee_name)
        self.send_operation(OpCodes.skip_breakpoint, data)

    def send_operation(self, opcode, data):
        raise NotImplementedError

    def process_operation(self, opcode, data):
        container_bee_name, read_bytes = unpack_pascal_string(data)

        if opcode == OpCodes.push_out:
            offset = read_bytes

            value, read_bytes = unpack_pascal_string(data, offset=offset)
            if callable(self.on_push_out):
                self.on_push_out(container_bee_name, value)

        elif opcode == OpCodes.trigger:
            if callable(self.on_push_out):
                self.on_trigger(container_bee_name)

        elif opcode == OpCodes.pretrigger:
            if callable(self.on_push_out):
                self.on_pretrigger(container_bee_name)

        # We've hit a breakpoint!
        if container_bee_name in self.breakpoints:
            if callable(self.on_breakpoint_hit):
                self.on_breakpoint_hit(container_bee_name)


class RemoteDebugSession:
    debug_controller_class = HivemapDebugController

    def __init__(self):
        self._container_id_to_filepath = {}
        self._filepath_to_container_id = {}

        self._breakpoints = {}
        self._debug_controllers = {}

        self.on_created_controller = None
        self.on_destroyed_controller = None

        self._request_close = None
        self._send_data = None

    def is_debugging_hivemap(self, file_path):
        sanitised = self._sanitise_path(file_path)
        return sanitised in self._filepath_to_container_id

    def _create_hivemap_controller(self, container_id, file_path):
        # Create debug controller
        controller = self.__class__.debug_controller_class(file_path)
        controller.send_operation = partial(self._send_data_from, container_id)
        controller._request_close = self.close

        if callable(self.on_created_controller):
            self.on_created_controller(controller)

        return controller

    def _on_received_register_container_id(self, container_id, file_path):
        sanitised_path = self._sanitise_path(file_path)

        self._container_id_to_filepath[container_id] = sanitised_path
        self._filepath_to_container_id[sanitised_path] = container_id

        self._debug_controllers[container_id] = self._create_hivemap_controller(container_id, sanitised_path)

    def _send_data_from(self, container_id, opcode, data):
        full_data = pack('BB', opcode, container_id) + data
        self._send_data(full_data)

    @staticmethod
    def _sanitise_path(file_path):
        return os.path.normpath(file_path)

    def process_data(self, data):
        opcode, = unpack_from('B', data)
        offset = 1

        if opcode == OpCodes.register_root:
            file_path, read_bytes = unpack_pascal_string(data, offset=offset)
            offset += read_bytes

            container_id, = unpack_from('B', data, offset=offset)
            offset += 1

            self._on_received_register_container_id(container_id, file_path)

        else:
            container_id, = unpack_from('B', data, offset=offset)
            offset += 1

            debug_controller = self._debug_controllers[container_id]
            remaining_data = data[offset:]

            debug_controller.process_operation(opcode, remaining_data)

    def on_closed(self):
        for controller in self._debug_controllers.values():
            controller.on_closed()

            if callable(self.on_destroyed_controller):
                self.on_destroyed_controller(controller)

    def close(self):
        self._request_close()


class RemoteDebugServer:

    session_class = RemoteDebugSession

    def __init__(self, host=None, port=None):
        self._server = Server(host, port)
        self._server.on_received = self._on_received
        self._server.on_connected = self._on_connected
        self._server.on_disconnected = self._on_disconnected

        self.on_created_session = None
        self.on_closed_session = None

        self._session = None
        self._server.launch()

    def add_breakpoint(self, root_hive_id, bee_name):
        pass

    @property
    def session(self):
        return self._session

    def _create_session(self):
        session = self.__class__.session_class()
        session._send_data = partial(self._send_data, session)
        session._request_close = partial(self._session_request_close, session)

        if callable(self.on_created_session):
            self.on_created_session(session)

        return session

    def _session_request_close(self, session):
        self._close_session(session)
        self._server.disconnect()

    def _close_session(self, session):
        if session is not self._session:
            raise RuntimeError("Session not active session")

        session.on_closed()

        if callable(self.on_closed_session):
            self.on_closed_session(session)

        session._request_close = None
        session._send_data = None

        self._session = None

    def _send_data(self, session, data):
        if session is not self._session:
            raise RuntimeError("No active session")

        self._server.send(data)

    def _on_received(self, data):
        if self._session is None:
            raise RuntimeError("No active session")

        self._session.process_data(data)

    def _on_connected(self):
        if self._session is not None:
            raise RuntimeError("Expected no active session")

        self._session = self._create_session()

    def _on_disconnected(self):
        if self._session is None:
            return

        self._close_session(self._session)
