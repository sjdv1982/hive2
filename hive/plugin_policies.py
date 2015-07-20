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

    def pre_donated(self):
        pass

    is_satisfied = True


class _SinglePluginPolicy(PluginPolicy):

    def pre_donated(self):
        if self._counter:
            raise PluginPolicyError("Plugin already donated")


class SingleRequired(_SinglePluginPolicy):

    @property
    def is_satisfied(self):
        return self._counter == 1


class SingleOptional(_SinglePluginPolicy):

    @property
    def is_satisfied(self):
        return 0 <= self._counter <= 1


class MultipleRequired(PluginPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 1


class MultipleOptional(PluginPolicy):

    pass

