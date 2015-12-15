"""Plugin donation policies.

Defines policies for plugin donation
"""


class PluginPolicyError(Exception):
    pass


class PluginPolicy:

    def __init__(self):
        self._counter = 0

    def on_donated(self):
        self._counter += 1

    @property
    def is_satisfied(self):
        raise NotImplemented

    def pre_filled(self):
        if self.is_satisfied:
            raise PluginPolicyError("Policy forbids further connections")

    def validate(self):
        if not self.is_satisfied:
            raise PluginPolicyError("Policy was not satisfied")


class SingleRequired(PluginPolicy):

    @property
    def is_satisfied(self):
        return self._counter == 1


class SingleOptional(PluginPolicy):

    @property
    def is_satisfied(self):
        return 0 <= self._counter <= 1


class MultipleRequired(PluginPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 1


class MultipleOptional(PluginPolicy):

    is_satisfied = True

