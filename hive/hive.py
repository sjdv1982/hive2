from ._compatability import next, is_method
from .classes import HiveInternals, HiveExportables, HiveArgs, ResolveBee, Method
from .mixins import *
from .manager import bee_register_context, get_mode, hive_mode_as, get_building_hive, building_hive_as, run_hive_as, \
    memoize
from .tuple_type import tuple_type, types_match

import inspect


def generate_bee_name():
    i = 0
    while True:
        i += 1
        yield "bee {}".format(i)


it_generate_bee_name = generate_bee_name()


def bee_sort_key(item):
    b = item[0]
    k = b
    if b.startswith("bee"):
        try:
            int(b[3:])
            k = "zzzzzzz" + b

        except ValueError:
            pass

    return k


class HiveMethodWrapper(object):
    """Intercept attribute lookups to return wrapped methods belonging to a given class."""

    def __init__(self, cls):
        object.__setattr__(self, "_cls", cls)

    def __getattr__(self, attr):
        value = getattr(self._cls, attr)

        if is_method(value):
            return Method(self._cls, value)

        else:
            return value

    def __setattr__(self, attr):
        raise AttributeError("HiveMethodWrapper of class '{}' is read-only".format(self._cls.__name__))


class Generic(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        return str(self.__dict__)


class RuntimeHive(ConnectSourceDerived, ConnectTargetDerived, TriggerSource, TriggerTarget):
    """Unique Hive instance that is created at runtime for a Hive object.

    Lightweight instantiation is supported through caching performed by the HiveObject instance.
    """

    def __init__(self, hive_object, builders):
        self._hive_bee_name = hive_object._hive_bee_name
        self._hive_object = hive_object
        self._hive_build_class_instances = {}
        self._hive_bee_instances = {}
        self._bee_names = ["_drones"]
        self._drones = []

        with run_hive_as(self):
            for builder, builder_cls in builders:
                args = hive_object._hive_builder_args
                kwargs = hive_object._hive_builder_kwargs

                if builder_cls is not None:
                    assert builder_cls not in self._hive_build_class_instances, builder_cls

                    # Do not initialise instance yet
                    build_class_instance = builder_cls.__new__(builder_cls)

                    self._hive_build_class_instances[builder_cls] = build_class_instance
                    self._drones.append(build_class_instance)

                    build_class_instance.__init__(*args, **kwargs)

            with building_hive_as(hive_object), hive_mode_as("build"):
                # Add external bees to runtime hive
                bees = []
                external_bees = hive_object._hive_ex

                for bee_name in external_bees:
                    bee = getattr(external_bees, bee_name)
                    exported_bee = bee.export()

                    # TODO: nice exception reporting
                    instance = exported_bee.getinstance(self._hive_object)

                    if isinstance(instance, Bindable):
                        instance = instance.bind(self)

                    bees.append((bee_name, instance))

                # Add internal bees (that are hives, Callable or Stateful) to runtime hive
                internal_bees = hive_object._hive_i

                for bee_name in internal_bees:
                    bee = getattr(internal_bees, bee_name)
                    private_name = "_" + bee_name

                    # Some runtime hive attributes are protected
                    assert not hasattr(self, private_name), private_name

                    # TODO: nice exception reporting
                    instance = bee.getinstance(self._hive_object)
                    if isinstance(instance, Bindable):
                        instance = instance.bind(self)
                        if instance is None:
                            continue

                        instance.parent = self

                    if isinstance(bee, HiveObject) or bee.implements(Callable):
                        bees.append((private_name, instance))

                for bee_name, instance in bees:
                    if isinstance(instance, Stateful):
                        continue

                    instance._hive_bee_name = self._hive_bee_name + (bee_name,)
                    self._hive_bee_instances[bee_name] = instance
                    self._bee_names.append(bee_name)
                    setattr(self, bee_name, instance)

    @staticmethod
    def _hive_can_connect_hive(other):
        return isinstance(other, RuntimeHive)

    def _hive_find_connect_sources(self):
        return self._hive_object._hive_find_connect_sources()

    def _hive_find_connect_targets(self):
        return self._hive_object._hive_find_connect_targets()

    def _hive_trigger_source(self, target_func):
        source_name = self._hive_object._hive_find_trigger_source()
        instance = self._hive_bee_instances[source_name]
        return instance._hive_trigger_source(target_func)

    def _hive_trigger_target(self):
        target_name = self._hive_object._hive_find_trigger_target()
        instance = self._hive_bee_instances[target_name]
        return instance._hive_trigger_target()

    def _hive_get_connect_source(self, target):
        source_name = self._hive_object._hive_find_connect_source(target)
        return getattr(self, source_name)

    def _hive_get_connect_target(self, source):
        target_name = self._hive_object._hive_find_connect_target(source)
        return getattr(self, target_name)
      
    def implements(self, cls):
        return isinstance(self, cls)

    def __iter__(self):
        return iter(self._bee_names)

    def __dir__(self):
        return self._bee_names


class HiveObject(Exportable, ConnectSourceDerived, ConnectTargetDerived, TriggerSource, TriggerTarget):
    """Built Hive base-class responsible for creating new Hive instances.

    All bees defined with the builder functions are memoized and cached for faster instantiation
    """

    _hive_parent_class = None
    _hive_runtime_class = None
    _hive_bee_name = ()

    _hive_i = None
    _hive_ex = None
    _hive_args_frozen = None

    export_only = False

    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        self._hive_object_cls = get_building_hive()
        
        # TODO: filter args and kwargs based on _hive_args and _hive_hive_kwargs

        # Automatically import parent sockets and plugins
        self.auto_connect = kwargs.pop("auto_connect", False)

        # Args to instantiate builder-class instances
        self._hive_builder_args = args #for now
        self._hive_builder_kwargs = kwargs #for now
            
        # Check calling signature of builderclass.__init__
        init_plus_args = (None,) + self._hive_builder_args

        # Check build functions are valid
        for builder, builder_cls in self._hive_parent_class._builders:
            if builder_cls is not None and inspect.isfunction(builder_cls.__init__):
                try:
                    inspect.getcallargs(builder_cls.__init__, *init_plus_args, **self._hive_builder_kwargs)

                except TypeError as err:
                    raise TypeError("{}.{}".format(builder_cls.__name__, err.args[0]))

        with hive_mode_as("build"):
            external_bees = self.__class__._hive_ex
            for bee_name in external_bees:
                exportable = getattr(external_bees, bee_name)
                target = exportable.export()
                resolve_bee = ResolveBee(target, self)
                setattr(self, bee_name, resolve_bee)

        return self

    @memoize
    def getinstance(self, parent_hive_object):
        return self.instantiate()
    
    def instantiate(self):
        """Return an instance of the runtime Hive for this Hive object."""
        return self._hive_runtime_class(self, self._hive_parent_class._builders)

    @staticmethod
    def _hive_can_connect_hive(other):
        return isinstance(other, HiveObject)
    
    @classmethod
    def _hive_find_trigger_target(cls):
        """Find name of single external bee that supported TriggerTarget interface.

        Raise TypeError if such a condition cannot be met
        """
        external_bees = cls._hive_ex
        trigger_targets = []

        for bee_name in dir(external_bees):
            bee = getattr(external_bees, bee_name)
            exported_bee = bee.export()
            if isinstance(exported_bee, TriggerTarget):
                trigger_targets.append(bee_name)

        if not trigger_targets:
            raise TypeError("No trigger targets in %s" % cls)

        elif len(trigger_targets) > 1:
            raise TypeError("Multiple trigger targets in {}: {}".format(cls, trigger_targets))

        return trigger_targets[0]
        
    @classmethod
    def _hive_find_trigger_source(cls):
        """Find and return name of single external bee that supported TriggerSource interface.

        Raise TypeError if such a condition cannot be met
        """
        external_bees = cls._hive_ex
        trigger_sources = []

        for bee_name in external_bees:
            bee = getattr(external_bees, bee_name)
            exported_bee = bee.export()

            if isinstance(exported_bee, TriggerSource):
                trigger_sources.append(bee_name)

        if not trigger_sources:
            raise TypeError("No TriggerSources in %s" % cls)

        elif len(trigger_sources) > 1:
            raise TypeError("Multiple TriggerSources in %s: %s" % (cls, trigger_sources))

        return trigger_sources[0]

    @classmethod
    def _hive_find_connect_sources(cls):
        externals = cls._hive_ex

        # Find source hive ConnectSources
        connect_sources = []
        for bee_name in externals:
            bee = getattr(externals, bee_name)
            exported_bee = bee.export()

            if not exported_bee.implements(ConnectSource):
                continue

            candidate = Generic(attrib=bee_name, data_type=exported_bee.data_type)
            connect_sources.append(candidate)

        return connect_sources

    @classmethod
    def _hive_find_connect_targets(cls):
        externals = cls._hive_ex

        # Find target hive ConnectTargets
        connect_targets = []
        for bee_name in externals:
            bee = getattr(externals, bee_name)
            exported_bee = bee.export()

            if not exported_bee.implements(ConnectTarget):
                continue

            candidate = Generic(attrib=bee_name, data_type=exported_bee.data_type)
            connect_targets.append(candidate)

        return connect_targets

    @classmethod
    def _hive_find_connect_source(cls, target):
        """Find and return the name of a suitable connect source within this hive

        :param target: target to connect to
        """
        assert target.implements(ConnectTarget)
        target_data_type = tuple_type(target.data_type)

        connect_sources = [c for c in cls._hive_find_connect_sources() if types_match(c.data_type, target_data_type)]

        if not connect_sources:
            raise TypeError("No matching connection sources found for {}".format(target))

        elif len(connect_sources) > 1:
            raise TypeError("Multiple connection sources found for {}: {}".format(target, connect_sources))

        return connect_sources[0].attrib
            
    @classmethod
    def _hive_find_connect_target(cls, source):
        """Find and return the name of a suitable connect target within this hive

        :param source: source to connect to
        """
        assert source.implements(ConnectSource)
        source_data_type = tuple_type(source.data_type)

        connect_targets = [c for c in cls._hive_find_connect_targets() if types_match(c.data_type,source_data_type)]

        if not connect_targets:
            raise TypeError("No matching connections found for {}".format(source))

        elif len(connect_targets) > 1:            
            raise TypeError("Multiple connection targets found for {}: {}".format(source, connect_targets))

        return connect_targets[0].attrib

    def _hive_get_trigger_target(self):
        """Return single external bee that supported TriggerTarget interface"""
        trigger_name = self._hive_find_trigger_target()
        return getattr(self, trigger_name)

    def _hive_get_trigger_source(self):
        """Return single external bee that supported TriggerSource interface"""
        trigger_name = self._hive_find_trigger_source()
        return getattr(self, trigger_name)

    def _hive_get_connect_target(self, source):
        """Return single external bee that supported ConnectTarget interface"""
        target_name = self._hive_find_connect_target(source)
        return getattr(self, target_name)

    def _hive_get_connect_source(self, target):
        """Return single external bee that supported ConnectSource interface"""
        source_name = self._hive_find_connect_source(target)
        return getattr(self, source_name)

    def export(self):
        return self


class HiveBuilder(object):
    """Deferred Builder for constructing Hive classes.

    Perform building once for multiple instances of the same Hive.
    """

    _builders = ()
    _declarators = ()

    _hive_args = None
    _hive_hive_kwargs = False
    _hive_object_classes = {}

    def __new__(cls, *args, **kwargs):
        args, kwargs, hive_object_cls = cls._hive_get_hive_object_cls(args, kwargs)

        self = hive_object_cls(*args, **kwargs)

        if get_mode() == "immediate":
            return self.instantiate()

        else:
            return self

    @classmethod
    def extend(cls, name, builder, builder_cls=None, declarator=None, hive_kwargs=False):
        """Extend HiveObject with an additional builder (and builder class)

        :param name: name of new hive class
        :param builder: optional function used to build hive
        :param builder_cls: optional Python class to bind to hive
        :param declarator: optional declarator to establish parameters
        :param hive_kwargs: TODO
        """
        if builder_cls is not None:
            assert issubclass(builder_cls, object), "cls must be a new-style Python class, e.g. class SomeHive(object): ..."

        builders = cls._builders + ((builder, builder_cls),)

        if declarator is not None:
            declarators = cls._declarators + (declarator,)

        else:
            declarators = cls._declarators

        class_dict = {
            "_builders": builders,
            "_declarators": declarators,
            "_hive_hive_kwargs": hive_kwargs,
            "_hive_args": None,
            "_hive_object_classes": {}
        }

        return type(name, (cls,), class_dict)

    @classmethod
    def _hive_build(cls, parameter_values):
        """Build a HiveObject for this Hive, with appropriate Args instance

        :param kwargs: Parameter keyword arguments
        """
        hive_object_cls = type("{}::hive_object".format(cls.__name__), (HiveObject,), {"_hive_parent_class": cls})

        # Get frozen args
        frozen_args_wrapper = cls._hive_args.freeze(parameter_values)

        hive_object_cls._hive_i = internals = HiveInternals(hive_object_cls)
        hive_object_cls._hive_ex = externals = HiveExportables(hive_object_cls)
        hive_object_cls._hive_args_frozen = frozen_args_wrapper

        with hive_mode_as("build"), building_hive_as(hive_object_cls), bee_register_context() as registered_bees:
            # Invoke builder functions to build wrappers
            for builder, builder_cls in cls._builders:
                if builder_cls is not None:
                    wrapper = HiveMethodWrapper(builder_cls)
                    builder(wrapper, internals, externals, frozen_args_wrapper)

                else:
                    builder(internals, externals, frozen_args_wrapper)

            from .connect import connect

            auto_plugins = set()
            auto_sockets = set()

            # Find plugins and sockets
            for bee_name in externals:
                bee = getattr(externals, bee_name)

                if bee.implements(Plugin) and bee.auto_connect:
                    auto_plugins.add(bee)

                if bee.implements(Socket) and bee.auto_connect:
                    auto_sockets.add(bee)

            # Automatically connect plugins and sockets
            for bee_name in internals:
                bee = getattr(internals, bee_name)

                if not isinstance(bee, HiveObject):
                    continue

                if not bee.auto_connect:
                    continue

                for child_bee_name in bee._hive_ex:
                    child_bee = getattr(bee, child_bee_name)

                    is_socket = child_bee.implements(Socket)
                    is_plugin = child_bee.implements(Plugin)

                    if not (is_socket or is_plugin):
                        continue

                    if not child_bee.auto_connect:
                        continue

                    identifier = child_bee.identifier
                    if not identifier:
                        continue

                    data_type = child_bee.data_type

                    if is_socket:
                        for plugin in auto_plugins:
                            if plugin.identifier != identifier:
                                continue

                            if not types_match(data_type, plugin.data_type, allow_none=True):
                                continue

                            connect(plugin, child_bee)

                    else:
                        for socket in auto_sockets:
                            if socket.identifier != identifier:
                                continue

                            if not types_match(data_type, socket.data_type, allow_none=True):
                                continue

                            connect(child_bee, socket)

        # Find anonymous bees
        anonymous_bees = set(registered_bees)

        # Find any anonymous bees which are held on object
        for bee_name in internals:
            bee = getattr(internals, bee_name)

            if bee in anonymous_bees:
                anonymous_bees.remove(bee)

        # Save anonymous bees to internal wrapper, with unique names
        for bee in registered_bees:
            if bee not in anonymous_bees:
                continue

            # Find unique name for bee
            while True:
                bee_name = next(it_generate_bee_name)
                if not hasattr(internals, bee_name):
                    break

            setattr(internals, bee_name, bee)

        # TODO: auto-remove connections/triggers for which the source/target has been deleted
        # TODO: sockets and plugins, take options into account for namespaces

        # Build runtime hive class
        run_hive_class_dict = {}

        for bee_name in externals:
            bee = getattr(externals, bee_name)

            # If the bee requires a property interface, build a property
            if isinstance(bee, Stateful):
                run_hive_class_dict[bee_name] = property(bee._hive_stateful_getter, bee._hive_stateful_setter)

        hive_object_cls._hive_runtime_class = type("{}::run_hive".format(hive_object_cls.__name__), (RuntimeHive,),
                                                   run_hive_class_dict)
        return hive_object_cls

    @classmethod
    def _hive_build_args_wrapper(cls):
        cls._hive_args = args_wrapper = HiveArgs(cls)

        # Execute declarators
        with hive_mode_as("declare"):
            for declarator in cls._declarators:
                declarator(args_wrapper)

    @classmethod
    def _hive_get_hive_object_cls(cls, args, kwargs):
        """Find appropriate HiveObject for argument values

        Extract parameters from arguments and return remainder
        """
        if cls._hive_args is None:
            cls._hive_build_args_wrapper()

        # Map keyword arguments to parameters, return remaining arguments
        args, kwargs, parameter_values = cls._hive_args.extract_parameter_values(args, kwargs)

        # If a new combination of parameters is provided
        try:
            hive_object_cls = cls._hive_object_classes[parameter_values]

        except KeyError:
            hive_object_cls = cls._hive_build(parameter_values)
            cls._hive_object_classes[parameter_values] = hive_object_cls

        return args, kwargs, hive_object_cls


# TODO options for namespaces (old frame/hive distinction)
def hive(name, builder, cls=None, declarator=None, hive_kwargs=False):
    if cls is not None:
        assert issubclass(cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

    return HiveBuilder.extend(name, builder, cls, declarator, hive_kwargs)