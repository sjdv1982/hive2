import hive

from ..bind import BindInfo


class AppEnvironmentClass:

    def __init__(self, context):
        plugins = context.plugins['app']

        self._quit = plugins['quit']
        self._get_tick_rate = plugins['get_tick_rate']

    def quit(self):
        self._quit()

    def get_tick_rate(self):
        return self._get_tick_rate()


def declare_app_environment(meta_args):
    pass


def build_app_environment(cls, i, ex, args, meta_args):
    """Runtime app environment for instantiated hive.

    Provides appropriate sockets and plugins for app interface
    """
    ex.app_quit = hive.plugin(cls.quit, identifier="app.quit")
    ex.app_get_tick_rate = hive.plugin(cls.get_tick_rate, identifier="app.get_tick_rate")


AppEnvironment = hive.meta_hive("AppEnvironment", build_app_environment, declare_app_environment,
                                cls=AppEnvironmentClass)


class AppBindClass:

    def __init__(self):
        self._hive = hive.get_run_hive()

        self._plugins = {}

    def on_started(self):
        pass

    def on_stopped(self):
        pass

    def set_quit(self, quit):
        self._plugins['quit'] = quit

    def set_get_tick_rate(self, get_tick_rate):
        self._plugins['get_tick_rate'] = get_tick_rate

    def get_plugins(self):
        return {'app': self._plugins}


def declare_bind(meta_args):
    pass


def build_bind(cls, i, ex, args, meta_args):
    ex.get_quit = hive.socket(cls.set_quit, identifier="app.quit")
    ex.get_get_tick_rate = hive.socket(cls.set_get_tick_rate, identifier="app.get_tick_rate")

    ex.app_get_plugins = hive.plugin(cls.get_plugins, identifier="bind.get_plugins")


BindApp = hive.dyna_hive("BindApp", build_bind, declarator=declare_bind, cls=AppBindClass)


def get_environments(meta_args):
    return AppEnvironment,


bind_info = BindInfo("App", BindApp, get_environments)
