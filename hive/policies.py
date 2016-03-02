"""Plugin donation policies.

Defines policies for plugin donation
"""

from hive.exception import HiveException


class MatchmakingPolicyError(HiveException):
    pass


class MatchmakingPolicy(object):

    limits = (-1, -1)

    def __init__(self):
        self._counter = 0

    def on_connected(self):
        self._counter += 1

    @property
    def is_valid(self):
        lower, upper = self.limits
        count = self._counter

        valid = True

        if lower is not None:
            valid = count >= lower

        if upper is not None:
            valid = valid and count <= upper

        return valid

    def pre_connected(self):
        if self._counter == self.limits[-1]:
            raise MatchmakingPolicyError("Policy '{}' forbids further connections".format(self.__class__.__name__))

    def validate(self):
        if not self.is_valid:
            raise MatchmakingPolicyError("Policy '{}' was not satisfied".format(self.__class__.__name__))


class SingleRequired(MatchmakingPolicy):
    """One connection only must be established"""

    limits = (1, 1)


class SingleOptional(MatchmakingPolicy):
    """At most, one connection can be established"""

    limits = (None, 1)


class MultipleRequired(MatchmakingPolicy):
    """One or more connections must be established"""

    limits = (1, None)


class MultipleOptional(MatchmakingPolicy):
    """Any number of connections can be established"""

    limits = (None, None)

