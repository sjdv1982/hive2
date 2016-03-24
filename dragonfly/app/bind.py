import hive

from ..bind import BindInfo, BindClassDefinition


definition = BindClassDefinition()
definition.forward_plugin("app.quit")
definition.forward_plugin("app.get_tick_rate")

factory = definition.build("BindApp")

AppEnvironment = hive.meta_hive("AppEnvironment", factory.environment_builder, factory.environment_declarator,
                                 builder_cls=factory.create_environment_class())


class AppBindClass(factory.create_external_class()):

    def on_started(self):
        pass

    def on_stopped(self):
        pass


BindApp = hive.dyna_hive("BindApp", factory.external_builder, declarator=factory.external_declarator,
                         builder_cls=AppBindClass)


def get_environment(meta_args):
    return AppEnvironment


bind_info = BindInfo("App", BindApp, get_environment)
