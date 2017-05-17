from contextlib import contextmanager
from logging import getLogger
from enum import auto, IntEnum

from .observer import Observable


class IllegalCommandError(Exception):
    """Exception for command that could not be executed or reversed"""


class CommandStates(IntEnum):
    execute = auto()
    un_execute = auto()


class Command:

    def __init__(self, execute, un_execute):
        """Command object initialiser
        
        :param execute: execution callback
        :param un_execute: un-execution callback
        """
        self._execute = execute
        self._un_execute = un_execute

        self._allowed_state = CommandStates.un_execute

    def __repr__(self):
        return "<Command>\n\t{}\n\t{}".format(self._execute, self._un_execute)

    def execute(self):
        """Execute command in forward direction"""
        if self._allowed_state != CommandStates.execute:
            raise IllegalCommandError("Command has already been executed")

        self._allowed_state = CommandStates.un_execute
        self._execute()

    def un_execute(self):
        """Execute command in reverse direction"""
        if self._allowed_state != CommandStates.un_execute:
            raise IllegalCommandError("Command has already been un-executed")

        self._allowed_state = CommandStates.execute
        self._un_execute()


class RecursionGuard:
    """Simple context manager to keep track of depth from initial caller"""

    def __init__(self):
        self._depth = 0

    @property
    def depth(self):
        return self._depth

    def __enter__(self):
        self._depth += 1

    def __exit__(self, *args):
        self._depth -= 1


class CommandLogManager:

    on_updated = Observable()

    def __init__(self, name='<root>', logger=None):
        if logger is None:
            logger = getLogger("{}::{}".format(name, id(self)))

        self._logger = logger
        self._current_history = CommandLog(self._logger, name)
        # Guards to stop updates being triggered during composite operations,
        # or commands being recorded during undo/redo operations
        self._update_guard = RecursionGuard()
        self._push_guard = RecursionGuard()

    @property
    def command_id(self):
        return self._current_history.command_id

    @contextmanager
    def command_context(self, name):
        composite_name = "{}.{}".format(self._current_history.name, name)
        history = CommandLog(self._logger, name=composite_name)

        self._current_history, old_history = history, self._current_history
        yield self
        self._current_history = old_history

        # If anything useful was performed, record history object
        if history.has_commands:
            self.record_command(history.redo_all, history.undo_all)

    def record_command(self, execute, un_execute):
        """Add reversable operation to history
        
        :param execute: callback to invoke when command is applied
        :param un_execute: callback to invoke when command is reversed
        """
        if not self._push_guard.depth:
            self._current_history.record_command(execute, un_execute)
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
        if self._update_guard.depth:
            return

        with self._update_guard:
            self.on_updated(self.command_id)


class CommandLogError(Exception):
    pass


class CommandLog:
    """Linear log of reversible operations"""

    def __init__(self, logger, name="<main>", limit=200):
        self._commands = []
        self._index = -1
        self._limit = limit

        self._name = name
        self._logger = logger

    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    @property
    def has_commands(self):
        return bool(self._commands)

    @property
    def can_redo(self):
        return self._index < len(self._commands) - 1

    @property
    def can_undo(self):
        return self._index >= 0

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
            raise CommandLogError("Cannot undo any more operations")

        command = self._commands[self._index]
        self._index -= 1

        command.un_execute()

    def redo(self):
        if not self.can_redo:
            raise CommandLogError("Cannot redo any more operations")

        self._index += 1
        command = self._commands[self._index]

        command.execute()

    def record_command(self, execute, unexecute):
        command = Command(execute, unexecute)
        self._add_command(command)

    def _add_command(self, command):
        # If not at end of list, then later commands will be lost, as history must be contiguous in time
        if self._index < len(self._commands) - 1:
            del self._commands[self._index + 1:]
            latest_command = self._commands[-1]

            self._logger.info("Commands after {} have been lost due to an add command:\n{!r}"
                              .format(latest_command, command))

        self._commands.append(command)
        self._index += 1

        # Limit length to a maximum number of operations
        if len(self._commands) > self._limit:
            # Assume everything atomic, hence only one command to displace
            # Index must be at end, if command list has grown
            self._index -= 1
            del self._commands[0]

    def __repr__(self):
        return "<CommandLog ({})>".format(self.name)


