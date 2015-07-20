"""Socket donation policies.

Defines policies for socket fulfillment
"""


class SocketPolicyError(Exception):
    pass


class SocketPolicy:

    def __init__(self):
        self._counter = 0

    def pre_filled(self):
        pass

    def on_filled(self):
        self._counter += 1

    is_satisfied = True


class _SingleSocketPolicy(SocketPolicy):

    def pre_filled(self):
        if self._counter:
            raise SocketPolicyError("Socket already filled, requires single plugin")


class SingleRequired(_SingleSocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter == 1


class SingleOptional(_SingleSocketPolicy):

    @property
    def is_satisfied(self):
        return 0 <= self._counter <= 1


class MultipleRequired(SocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 1


class MultipleOptional(SocketPolicy):
    pass

