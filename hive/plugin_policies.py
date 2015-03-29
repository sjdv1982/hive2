"""Plugin donation policies.

Defines policies for plugin donation
"""


class PluginPolicy:

    def __init__(self):
        self._counter = 0

    @property
    def is_satisfied(self):
        return True

    def on_donated(self):
        self._counter += 1

    def pre_donated(self):
        pass


class _SinglePluginPolicy(PluginPolicy):

    def pre_donated(self):
        assert not self._counter, "Plugin already donated"


class SingleRequired(_SinglePluginPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 0


class SingleOptional(_SinglePluginPolicy):

    @property
    def is_satisfied(self):
        return True


class MultipleRequired(PluginPolicy):

    @property
    def is_satisfied(self):
        return self._counter > 1


class MultipleOptional(PluginPolicy):

    @property
    def is_satisfied(self):
        return True

