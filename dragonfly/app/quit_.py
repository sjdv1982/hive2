import hive


class _Quit:

    def __init__(self):
        self._quit = None

    def set_quit(self, do_quit):
        self._quit = do_quit

    def quit(self):
        self._quit()


def build_quit(cls, i, ex, args):
    """Quit the running environment"""
    ex.get_quit = hive.socket(cls.set_quit, ("quit",))

    i.do_quit = hive.triggerable(cls.quit)
    ex.do_quit = hive.entry(i.do_quit)


Quit = hive.hive("Quit", build_quit, cls=_Quit)
