class DebugBeeBase:

    def __init__(self, debug_context, source_ref, target_ref):
        self._debug_context = debug_context
        self._source_ref = source_ref
        self._target_ref = target_ref


class DebugPushOutTarget(DebugBeeBase):

    def __getattr__(self, name):
        return getattr(self._target_ref(), name)

    def push(self, value):
        self._debug_context.report_push_out(self._source_ref, self._target_ref, value)
        self._target_ref().push(value)


class DebugPullInSource(DebugBeeBase):

    def __getattr__(self, name):
        return getattr(self._source_ref(), name)

    def pull(self):
        # TODO: exception handling hooks
        self._pretrigger.push()
        value = self._get_value()

        self._debug_context.report_pull_in(self._source_ref, self._target_ref, value)

        self._trigger.push()
        return value


class DebugTriggerTarget(DebugBeeBase):

    def __call__(self):
        self._debug_context.report_trigger(self._source_ref, self._target_ref,)


class DebugPretriggerTarget(DebugBeeBase):

    def __call__(self):
        self._debug_context.report_pretrigger(self._source_ref, self._target_ref,)