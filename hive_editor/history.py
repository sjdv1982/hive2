from contextlib import contextmanager
from logging import getLogger


def unique_id_counter():
    i = 0

    while True:
        yield i
        i += 1


class IllegalCommandError(Exception):
    pass


class CommandStates:
    execute, unexecute = range(2)


class Command:

    def __init__(self, execute, unexecute):
        self._execute = execute
        self._unexecute = unexecute

        self._allowed_state = CommandStates.unexecute

    def __repr__(self):
        return "<Command>\n\t{}\n\t{}".format(self._execute, self._unexecute)

    def execute(self):
        if self._allowed_state != CommandStates.execute:
            raise IllegalCommandError("Command has already been executed")

        self._allowed_state = CommandStates.unexecute
        self._execute()

    def unexecute(self):
        if self._allowed_state != CommandStates.unexecute:
            raise IllegalCommandError("Command has already been unexecuted")

        self._allowed_state = CommandStates.execute
        self._unexecute()


class RecursionGuard:

    def __init__(self):
        self._depth = 0

    @property
    def depth(self):
        return self._depth

    @property
    def is_busy(self):
        return bool(self._depth)

    def __enter__(self):
        self._depth += 1

    def __exit__(self, *args):
        self._depth -= 1


class CommandHistoryManager:

    def __init__(self, name='<root>', logger=None):
        if logger is None:
            logger = getLogger("{}::{}".format(name, id(self)))

        self._logger = logger

        self._current_history = CommandHistory(self._logger, name)

        self._update_guard = RecursionGuard()
        self._push_guard = RecursionGuard()

        self.on_updated = None

    @property
    def command_id(self):
        return self._current_history.command_id

    @contextmanager
    def command_context(self, name):
        composite_name = "{}.{}".format(self._current_history.name, name)
        history = CommandHistory(self._logger, name=composite_name)

        self._current_history, old_history = history, self._current_history
        yield
        self._current_history = old_history

        self.record_command(history.redo_all, history.undo_all)

    def record_command(self, execute, unexecute):
        """Add reversable operation to history"""
        if not self._push_guard.is_busy:
            self._current_history.record_command(execute, unexecute)
            self._on_updated()

    def undo(self):
        with self._push_guard:
            self._current_history.undo()

        self._on_updated()

    def redo(self):
        with self._push_guard:
            self._current_history.redo()

        self._on_updated()

    def _on_updated(self):
        if self._update_guard.is_busy:
            return

        with self._update_guard:
            if callable(self.on_updated):
                self.on_updated(self.command_id)


class OperationHistoryError(Exception):
    pass


class CommandHistory:

    def __init__(self, logger, name="<main>", limit=200):
        self._commands = []
        self._index = -1
        self._limit = limit

        self._name = name
        self._logger = logger

    @property
    def can_redo(self):
        return self._index < len(self._commands) - 1

    @property
    def can_undo(self):
        return self._index >= 0

    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    @property
    def command_id(self):
        if not 0 <= self._index < len(self._commands):
            return id(self)

        command = self._commands[self._index]
        return id(command)

    def undo_all(self):
        while self.can_undo:
            self.undo()

    def redo_all(self):
        while self.can_redo:
            self.redo()

    def undo(self):
        if not self.can_undo:
            raise OperationHistoryError("Cannot undo any more operations")

        command = self._commands[self._index]
        command.unexecute()

        self._index -= 1

    def redo(self):
        if not self.can_redo:
            raise OperationHistoryError("Cannot redo any more operations")

        self._index += 1

        command = self._commands[self._index]
        command.execute()

    def record_command(self, execute, unexecute):
        command = Command(execute, unexecute)
        self._add_command(command)

    def _add_command(self, command):
        # If not at end of stack
        if self._index < len(self._commands) - 1:
            latest_command = self._commands[self._index]

            self._logger.info("Commands after {} have been lost due to an add command".format(latest_command))
            del self._commands[self._index + 1:]

        self._commands.append(command)
        self._index += 1

        # Limit length
        if len(self._commands) > self._limit:
            # Assume everything atomic, hence only one command to displace
            # Index must be at end, if command list has grown
            self._index -= 1
            del self._commands[0]

    def __repr__(self):
        return "<History ({})>".format(self.name)


