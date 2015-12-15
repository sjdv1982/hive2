"""Socket donation policies.

Defines policies for socket fulfillment
"""


class SocketPolicyError(Exception):
    pass


class SocketPolicy:

    def __init__(self):
        self._counter = 0

    @property
    def is_satisfied(self):
        raise NotImplementedError

    def on_filled(self):
        self._counter += 1

    def pre_filled(self):
        if self.is_satisfied:
            raise SocketPolicyError("Policy forbids further connections")

    def validate(self):
        if not self.is_satisfied:
            raise SocketPolicyError("Policy was not satisfied")


class SingleRequired(SocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter == 1


class SingleOptional(SocketPolicy):

    @property
    def is_satisfied(self):
        return 0 <= self._counter <= 1


class MultipleRequired(SocketPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 1


class MultipleOptional(SocketPolicy):
    is_satisfied = True

