from contextlib import contextmanager


def unique_id_counter():
    i = 0
    while True:
        yield i
        i += 1


class HistoryManager:

    def __init__(self, name='<root>'):
        self._current_history = AtomicOperationHistory(name=name)
        self._is_guarded = False

        self.on_updated = None

    @contextmanager
    def guarded(self):
        """Guard history and ignore undo/redo operations"""
        self._is_guarded = True
        yield
        self._is_guarded = False

    @property
    def operation_id(self):
        return self._current_history.operation_id

    def undo(self):
        with self.guarded():
            self._current_history.undo()

        if callable(self.on_updated):
            self.on_updated(self)

    def redo(self):
        with self.guarded():
            self._current_history.redo()

        if callable(self.on_updated):
            self.on_updated(self)

    @contextmanager
    def composite_operation(self, name):
        composite_name = "{}.{}".format(self._current_history.name, name)
        history = AtomicOperationHistory(name=composite_name)
        self._current_history, old_history = history, self._current_history

        yield

        self._current_history = old_history
        old_history.push_operation(history.redo_all, (), history.undo_all, ())

    def push_operation(self, op, args, reverse_op, reverse_args):
        """Add reversable operation to history"""
        if self._is_guarded:
            return

        self._current_history.push_operation(op, args, reverse_op, reverse_args)

        if callable(self.on_updated):
            self.on_updated(self)


class AtomicOperationHistory:

    def __init__(self, limit=200, name="<main>"):
        self._operations = []
        self._index = -1
        self._limit = limit

        self._id_counter = unique_id_counter()
        self._operation_id = 0
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    @property
    def cant_redo(self):
        return self._index >= (len(self._operations) - 1)

    @property
    def cant_undo(self):
        return self._index < 0

    @property
    def operation_id(self):
        try:
            operation = self._operations[self._index]

        except IndexError:
            return 0

        else:
            return operation[-1]

    def undo_all(self):
        while not self.cant_undo:
            self.undo()

    def redo_all(self):
        while not self.cant_redo:
            self.redo()

    def undo(self):
        if self.cant_undo:
            raise ValueError("Cannot undo any more operations")

        last_operation = self._operations[self._index]
        op, args, reverse_op, reverse_args, op_id = last_operation
        reverse_op(*reverse_args)

        self._index -= 1

    def redo(self):
        if self.cant_redo:
            raise ValueError("Cannot redo any more operations")

        self._index += 1

        operation = self._operations[self._index]

        op, args, reverse_op, reverse_args, op_id = operation
        op(*args)

    def push_operation(self, op, args, reverse_op, reverse_args):
        operation_id = "{}.{}".format(self._name, next(self._id_counter))
        self._push_operation((op, args, reverse_op, reverse_args, operation_id))

    def _push_operation(self, operation):
        # If in middle of redo/undo
        if self._index < len(self._operations) - 1:
            print("Lost data after", self._index, len(self._operations))
            self._operations[:] = self._operations[:self._index + 1]

        self._operations.append(operation)
        self._index += 1

        # Limit length
        if len(self._operations) > self._limit:
            shift = len(self._operations) - self._limit

            self._index -= shift
            if self._index < 0:
                self._index = 0

            self._operations[:] = self._operations[shift:]

    def __repr__(self):
        ops = "\n\t".join([str(o) for o in self._operations])
        ops = "\n\t".join(ops.split("\n"))
        return "<History ({})>\n\t\t{}".format(self.name, ops)


