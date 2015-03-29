"""Socket donation policies.

Defines policies for socket fulfillment
"""


class SocketPolicy:

    def __init__(self):
        self._counter = 0

    def pre_filled(self):
        pass

    def on_filled(self):
        self._counter += 1

    @property
    def is_satisfied(self):
        return True


class SingleRequired(SocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 0

    def pre_filled(self):
        assert not self._counter, "Socket already filled"


class SingleOptional(SocketPolicy):

    @property
    def is_satisfied(self):
        return True


class MultipleRequired(SocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 1


class MultipleOptional(SocketPolicy):

    @property
    def is_satisfied(self):
        return True

