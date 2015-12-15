"""Socket donation policies.

Defines policies for socket fulfillment
"""


class SocketPolicyError(Exception):
    pass


class SocketPolicy:

    def __init__(self):
        self._counter = 0

    def on_filled(self):
        self._counter += 1

    @property
    def is_satisfied(self):
        raise NotImplementedError


class Required(SocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter == 1


class Optional(SocketPolicy):

    @property
    def is_satisfied(self):
        return 0 <= self._counter <= 1


class MultipleRequired(SocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 1


class MultipleOptional(SocketPolicy):
    is_satisfied = True

