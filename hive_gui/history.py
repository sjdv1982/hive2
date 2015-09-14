from contextlib import contextmanager


class OperationHistory:

    def __init__(self):
        self._history = AtomicOperationHistory()
        self._guard = False

    @contextmanager
    def guarded(self):
        self._guard = True
        yield
        self._guard = False

    def undo(self):
        with self.guarded():
            self._history.undo()

    def redo(self):
        with self.guarded():
            self._history.redo()

    @contextmanager
    def composite_operation(self, name):
        history = AtomicOperationHistory(name=name)

        self._history, old_history = history, self._history
        yield
        self._history = old_history

        old_history.push_history(history)

    def push_operation(self, *args, **kwargs):
        if self._guard:
            return

        self._history.push_operation(*args, **kwargs)


class AtomicOperationHistory:

    def __init__(self, limit=200, name="<main>"):
        self._operations = []
        self._index = -1
        self._limit = limit

        self.name = name

    @property
    def index(self):
        return self._index

    @property
    def cant_redo(self):
        return self._index >= (len(self._operations) - 1)

    @property
    def cant_undo(self):
        return self._index < 0

    def undo(self):
        if self.cant_undo:
            return

        last_operation = self._operations[self._index]

        if isinstance(last_operation, self.__class__):
            while not last_operation.cant_undo:
                last_operation.undo()

        else:
            op, args, reverse_op, reverse_args = last_operation
            try:
                reverse_op(*reverse_args)
            except Exception:
                print(self.name)
                raise

        self._index -= 1

    def redo(self):
        if self.cant_redo:
            return

        self._index += 1

        operation = self._operations[self._index]
        if isinstance(operation, self.__class__):

            while not operation.cant_redo:
                operation.redo()

        else:
            op, args, reverse_op, reverse_args = operation

            op(*args)

    def push_history(self, history):
        self._push_operation(history)

    def push_operation(self, op, args, reverse_op, reverse_args):
        self._push_operation((op, args, reverse_op, reverse_args))

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


