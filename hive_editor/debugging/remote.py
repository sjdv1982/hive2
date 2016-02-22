import os
from collections import namedtuple, defaultdict
from collections.abc import KeysView
from errno import ECONNRESET
from functools import lru_cache, partial
from itertools import product
from logging import getLogger
from queue import Queue, Empty
from socket import AF_INET, SOCK_STREAM, socket, error as SOCK_ERROR
from struct import pack, unpack_from, calcsize
from threading import Event, Thread
from weakref import WeakKeyDictionary, ref

from hive.debug import DebugContextBase
from hive.mixins import Nameable
from hive.ppin import PullIn
from hive.ppout import PushOut
from .utils import pack_pascal_string, unpack_pascal_string
from ..importer import get_hook
from ..models import model

HivemapConnection = namedtuple("Connection", "from_node from_name to_node to_name")


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
        super(Server, self).__init__()

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


class DebugNode:

    def __init__(self, debug_context, source_ref, target_ref):
        self._debug_context = debug_context
        self._source_ref = source_ref
        self._target_ref = target_ref


class DebugPushOutTarget(DebugNode):

    def __getattr__(self, name):
        return getattr(self._target_ref(), name)

    def push(self, value):
        self._debug_context.report_push_out(self._source_ref, self._target_ref, value)
        self._target_ref().push(value)


class DebugPullInSource(DebugNode):

    def __getattr__(self, name):
        return getattr(self._source_ref(), name)

    def pull(self):
        # TODO: exception handling hooks
        self._pretrigger.push()
        value = self._get_value()

        self._debug_context.report_pull_in(self._source_ref, self._target_ref, value)

        self._trigger.push()
        return value


class DebugTriggerTarget(DebugNode):

    def __call__(self):
        self._debug_context.report_trigger(self._source_ref, self._target_ref,)


class DebugPretriggerTarget(DebugNode):

    def __call__(self):
        self._debug_context.report_pretrigger(self._source_ref, self._target_ref,)


ContainerCandidates = namedtuple("ContainerCandidates", "containers paths")
ContainerPairInfo = namedtuple("PairInfo", "source_container_name target_container_name hivemap_path")
ContainerBeeReference = namedtuple("ContainerBeeReference", "container_id bee_container_name")


class RemoteDebugContext(DebugContextBase):

    def __init__(self, logger=None, host=None, port=None):
        self._container_hives = WeakKeyDictionary()
        self._container_hive_ref_to_id = {}

        self._id_generator = id_generator()

        self._client = Client(host, port)
        self._client.launch()
        self._client.on_received = self._on_received_response
        self._client.on_disconnected = self._on_disconnected

        self._breakpoints = {}
        if logger is None:
            logger = getLogger(repr(self))

        self._logger = logger

    def _clear_breakpoints(self):
        for breakpoint in self._breakpoints.values():
            self._unset_breakpoint(breakpoint)

        self._breakpoints.clear()

    def _on_disconnected(self):
        self._clear_breakpoints()

    def report_trigger(self, source_bee_ref, target_ref):
        self._on_operation(OpCodes.trigger, source_bee_ref, target_ref)

    def report_pretrigger(self, source_bee_ref, target_ref):
        self._on_operation(OpCodes.pretrigger, source_bee_ref, target_ref)

    def report_push_out(self, source_bee_ref, target_ref, data):
        self._on_operation(OpCodes.push_out, source_bee_ref, target_ref, data)

    def report_pull_in(self, source_bee_ref, target_ref, data):
        self._on_operation(OpCodes.pull_in, source_bee_ref, target_ref, data)

    def build_connection(self, source, target):
        if isinstance(source, PushOut):
            target = DebugPushOutTarget(self, ref(source), ref(target))

        elif isinstance(target, PullIn):
            source = DebugPullInSource(self, ref(source), ref(target))

        target._hive_connect_target(source)
        source._hive_connect_source(target)

    def build_trigger(self, source, target, pre):
        target_func = target._hive_trigger_target()

        if pre:
            callable_target = DebugPretriggerTarget(self, ref(source), ref(target))
            source._hive_pretrigger_source(callable_target)
            source._hive_pretrigger_source(target_func)

        else:
            callable_target = DebugTriggerTarget(self, ref(source), ref(target))
            source._hive_trigger_source(callable_target)
            source._hive_trigger_source(target_func)

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
        container_id, = unpack_from('B', message)
        bee_container_name, read_bytes = unpack_pascal_string(message, 1)

        print("DBG::Add breakpoint!", [bee_container_name])

        bee_container_ref = container_id, bee_container_name
        self._breakpoints[bee_container_ref] = Event()

    def _remove_breakpoint(self, message):
        container_id, = unpack_from('B', message)
        bee_container_name, read_bytes = unpack_pascal_string(message, 1)
        print("DBG::Remove breakpoint!", [bee_container_name])

        bee_container_ref = container_id, bee_container_name
        breakpoint = self._breakpoints.pop(bee_container_ref)
        self._unset_breakpoint(breakpoint)

    def _skip_breakpoint(self, message):
        container_id, = unpack_from('B', message)
        bee_container_name, read_bytes = unpack_pascal_string(message, 1)

        bee_container_ref = container_id, bee_container_name
        breakpoint = self._breakpoints[bee_container_ref]

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

    def _send_operation(self, opcode, root_hive_id, source_container_name, target_container_name, data):
        serialised = pack('B', root_hive_id) + pack_pascal_string(source_container_name) + \
                     pack_pascal_string(target_container_name)

        if opcode != OpCodes.trigger:
            serialised += pack_pascal_string(repr(data))

        self._send_command(opcode, serialised)

    def _send_container_hive_id(self, root_hive_id, container_hive_path):
        data = pack_pascal_string(container_hive_path) + pack('B', root_hive_id)
        self._send_command(OpCodes.register_root, data)

    def _send_hit_breakpoint(self, root_hive_id, container_name):
        data = pack('B', root_hive_id) + pack_pascal_string(container_name)
        self._send_command(OpCodes.hit_breakpoint, data)

    @staticmethod
    def _find_container_candidates(bee):
        if not isinstance(bee, Nameable):
            raise TypeError("Bee is not Nameable")

        paths = defaultdict(set)

        bee_runtime_infos = bee._hive_runtime_info
        if bee_runtime_infos is not None:
            for info in bee._hive_runtime_info:
                parent_ref, bee_name = info
                parent = parent_ref()

                parent_runtime_infos = parent._hive_runtime_info
                if parent_runtime_infos is None:
                    continue

                for parent_info in parent._hive_runtime_info:
                    container_ref, node_name = parent_info

                    paths[container_ref].add((node_name, bee_name))

        return paths

    @staticmethod
    def _format_container_path(name_path):
        x, y = name_path
        return "{}.{}".format(x.lstrip('_'), y.lstrip('_'))

    @lru_cache()
    def _get_hivemap_connections(self, file_path):
        hivemap = model.Hivemap.fromfile(file_path)
        name_to_hive = {hive.identifier: hive for hive in hivemap.hives}

        connections = set()

        for connection in hivemap.connections:
            from_identifier = connection.from_node
            to_identifier = connection.to_node

            if from_identifier not in name_to_hive:
                continue

            if to_identifier not in name_to_hive:
                continue

            connection = HivemapConnection(from_identifier, connection.output_name, to_identifier, connection.input_name)
            connections.add(connection)

        return connections

    @lru_cache()
    def _find_container_pair_info(self, source_bee_ref, target_bee_ref):
        source_bee = source_bee_ref()
        target_bee = target_bee_ref()

        source_candidates = self._find_container_candidates(source_bee)
        target_candidates = self._find_container_candidates(target_bee)

        containers = set(source_candidates).intersection(target_candidates)

        try:
            containing_hive_ref = containers.pop()

        except KeyError:
            self._logger.warn("Bee is not a container member")
            return None

        assert not containers, "Containers cannot have multiple intersections!"

        try:
            parent_builder_class = containing_hive_ref()._hive_object._hive_parent_class

        except AttributeError:
            self._logger.warn("Bee is not a container member")
            return None

        # Find hivemap file path
        importer = get_hook()
        get_file_path = importer.get_path_of_class

        # If this fails, not a hivemap hive
        try:
            file_path = get_file_path(parent_builder_class)

        except ValueError:
            return None

        connections = self._get_hivemap_connections(file_path)

        # Iterate over potential combinations of source names and target names.
        # If they are found in the hivemap connection set, these are the valid names
        for source_name, target_name in product(source_candidates[containing_hive_ref],
                                                target_candidates[containing_hive_ref]):
            candidate = HivemapConnection(*(source_name + target_name))
            if candidate not in connections:
                continue

            source_bee_name = "{}.{}".format(*source_name)
            target_bee_name = "{}.{}".format(*target_name)
            return ContainerPairInfo(source_bee_name, target_bee_name, file_path)

    @lru_cache()
    def _get_container_hive_id(self, container_hive_path):
        hive_id = next(self._id_generator)
        self._send_container_hive_id(hive_id, container_hive_path)
        return hive_id

    def _on_operation(self, opcode, source_bee_ref, target_bee_ref, data=None):
        container_pair_info = self._find_container_pair_info(source_bee_ref, target_bee_ref)

        if container_pair_info is None:
            return

        container_hive_id = self._get_container_hive_id(container_pair_info.hivemap_path)

        print("DBG::Report", container_pair_info, opcode)

        # Send operation ...
        self._send_operation(opcode, container_hive_id, container_pair_info.source_container_name,
                             container_pair_info.target_container_name, data)

        self._check_for_breakpoint(container_pair_info.source_container_name, container_hive_id,
                                   container_pair_info.hivemap_path)
        self._check_for_breakpoint(container_pair_info.target_container_name, container_hive_id,
                                   container_pair_info.hivemap_path)

    def _check_for_breakpoint(self, bee_container_name, container_hive_id, hivemap_path):
        # Check for breakpoint on pin
        bee_container_ref = container_hive_id, bee_container_name

        try:
            breakpoint = self._breakpoints[bee_container_ref]

        except KeyError:
            return

        self._send_hit_breakpoint(container_hive_id, bee_container_name)
        file_name = os.path.basename(hivemap_path)

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
        source_container_name, read_bytes = unpack_pascal_string(data)
        offset = read_bytes

        if opcode == OpCodes.hit_breakpoint:
            if callable(self.on_breakpoint_hit):
                self.on_breakpoint_hit(source_container_name)

        else:
            target_container_name, read_bytes = unpack_pascal_string(data, offset=offset)
            offset += read_bytes

            if opcode == OpCodes.push_out:
                value, read_bytes = unpack_pascal_string(data, offset=offset)
                if callable(self.on_push_out):
                    self.on_push_out(source_container_name, target_container_name, value)

            elif opcode == OpCodes.pull_in:
                value, read_bytes = unpack_pascal_string(data, offset=offset)
                if callable(self.on_push_out):
                    self.on_pull_in(source_container_name, target_container_name, value)

            elif opcode == OpCodes.trigger:
                if callable(self.on_push_out):
                    self.on_trigger(source_container_name, target_container_name)

            elif opcode == OpCodes.pretrigger:
                if callable(self.on_push_out):
                    self.on_pretrigger(source_container_name, target_container_name)


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
