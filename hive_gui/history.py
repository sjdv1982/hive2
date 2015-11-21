from contextlib import contextmanager


def unique_id_counter():
    i = 0
    while True:
        yield i
        i += 1


class OperationHistory:

    def __init__(self):
        self._id_counter = unique_id_counter()
        self._history = AtomicOperationHistory(id_counter=self._id_counter)
        self._guard = False

        self._in_composite = False
        self.on_updated = None

    @contextmanager
    def guarded(self):
        self._guard = True
        yield
        self._guard = False

    @property
    def operation_id(self):
        return self._history.operation_id

    def undo(self):
        with self.guarded():
            self._history.undo()

        if callable(self.on_updated):
            self.on_updated(self)

    def redo(self):
        with self.guarded():
            self._history.redo()

        if callable(self.on_updated):
            self.on_updated(self)

    @contextmanager
    def composite_operation(self, name):
        self._in_composite = True
        history = AtomicOperationHistory(id_counter=self._id_counter, name=name)

        self._history, old_history = history, self._history
        yield
        self._history = old_history

        old_history.push_history(history)

        self._in_composite = False

    def push_operation(self, *args, **kwargs):
        if self._guard:
            return

        self._history.push_operation(*args, **kwargs)

        if callable(self.on_updated):
            self.on_updated(self)


class AtomicOperationHistory:

    def __init__(self, id_counter, limit=200, name="<main>"):
        self._operations = []
        self._index = -1
        self._limit = limit
        self._id_counter = id_counter
        self._operation_id = next(id_counter)

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

    @property
    def operation_id(self):
        try:
            operation = self._operations[self._index]

        except IndexError:
            pass

        else:
            if isinstance(operation, self.__class__):
                try:
                    return operation.operation_id

                except ValueError:
                    pass

            else:
                return operation[-1]

        return self._operation_id

    def undo(self):
        if self.cant_undo:
            return

        last_operation = self._operations[self._index]

        if isinstance(last_operation, self.__class__):
            while not last_operation.cant_undo:
                last_operation.undo()

        else:
            op, args, reverse_op, reverse_args, op_id = last_operation
            try:
                reverse_op(*reverse_args)
            except Exception:
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
            op, args, reverse_op, reverse_args, op_id = operation
            op(*args)

    def push_history(self, history):
        self._push_operation(history)

    def push_operation(self, op, args, reverse_op, reverse_args):
        self._push_operation((op, args, reverse_op, reverse_args, next(self._id_counter)))

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


