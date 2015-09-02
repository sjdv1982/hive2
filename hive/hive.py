from ._compatability import next, is_method
from .classes import HiveInternals, HiveExportables, HiveArgs, ResolveBee, Method
from .connect import connect
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


class RuntimeHiveInstantiator(Bindable):
    """Instantiator bee of runtime hives"""

    def __init__(self, hive_object):
        # TODO, maybe setattr for bee.getinstance(hive_object) in hive ex/i wrappers
        self._hive_object = hive_object

    @memoize
    def bind(self, run_hive):
        return self._hive_object.instantiate()


class RuntimeHive(ConnectSourceDerived, ConnectTargetDerived, TriggerSource, TriggerTarget):
    """Unique Hive instance that is created at runtime for a Hive object.

    Lightweight instantiation is supported through caching performed by the HiveObject instance.
    """

    _hive_bee_name = ()
    _hive_object = None
    _hive_build_class_instances = None
    _hive_bee_instances = None
    _bee_names = None
    _drones = None

    def __init__(self, hive_object, builders):
        self._hive_bee_name = hive_object._hive_bee_name
        self._hive_object = hive_object
        self._hive_build_class_instances = {}
        self._hive_bee_instances = {}
        self._bee_names = ["_drones"]
        self._drones = []

        with run_hive_as(self):
            # Build args
            args = hive_object._hive_builder_args
            kwargs = hive_object._hive_builder_kwargs

            for builder, builder_cls in builders:

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
                    if not bee.implements(Stateful):
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

                    # Risk that proxies rename instances
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

    _hive_args = None
    _hive_meta_args_frozen = None

    _hive_namespace = None
    _hive_parent_namespace = None

    export_only = False

    def __init__(self, *args, **kwargs):
        # HiveObject class for hive that contains this hive (not self.__class__)
        self._hive_object_cls = get_building_hive()
        
        # TODO: filter args and kwargs based on _hive_args and _hive_hive_kwargs

        # Automatically import parent sockets and plugins
        self._allow_import_namespace = kwargs.pop("import_namespace", False)

        # Take out args parameters
        args, kwargs, arg_values = self._hive_args.extract_from_args(args, kwargs)
        self._hive_args_frozen = self._hive_args.freeze(arg_values)

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

    @memoize
    def getinstance(self, parent_hive_object):
        return RuntimeHiveInstantiator(self)

    def instantiate(self):
        """Return an instance of the runtime Hive for this Hive object."""
        return self._hive_runtime_class(self, self._hive_parent_class._builders)

    def import_namespace(self, parent_namespace):
        """Import plugins from parent class"""
        if not self._allow_import_namespace:
            return

        self._hive_parent_namespace = parent_namespace

        # Self as resolved bee
        resolved_bee = parent_namespace['resolved_self']

        socket_names = self._hive_namespace['socket_names']
        plugin_names = self._hive_namespace['plugin_names']

        # Resolve sockets and plugins
        sockets = self._hive_namespace['sockets'] = {i: getattr(resolved_bee, n) for i, n in socket_names.items()}
        plugins = self._hive_namespace['plugins'] = {i: getattr(resolved_bee, n) for i, n in plugin_names.items()}

        parent_sockets = parent_namespace['sockets']
        parent_plugins = parent_namespace['plugins']

        connections = []

        # Connect at this layer
        for identifier, socket in sockets.items():
            if not socket.auto_connect:
                continue

            try:
                plugin = parent_plugins[identifier]
            except KeyError:
                continue

            if not plugin.auto_connect:
                continue

            connections.append((plugin, socket))

        for identifier, plugin in plugins.items():
            if not plugin.auto_connect:
                continue

            try:
                socket = parent_sockets[identifier]
            except KeyError:
                continue

            if not socket.auto_connect:
                continue

            connections.append((plugin, socket))

        for plugin, socket in connections:
            if not types_match(socket.data_type, plugin.data_type, allow_none=True):
                continue

            connect(plugin, socket)

        # Create aggregate namespace
        all_plugins = parent_plugins.copy()
        all_plugins.update(plugins)

        all_sockets = parent_sockets.copy()
        all_sockets.update(sockets)

        for bee_name in self._hive_ex:
            bee = getattr(self._hive_ex, bee_name)

            if not isinstance(bee, HiveObject):
                continue

            resolved_child_bee = getattr(resolved_bee, bee_name)
            imported_namespace = dict(sockets=all_sockets, plugins=all_plugins, resolved_self=resolved_child_bee)
            bee.import_namespace(imported_namespace)

        for bee_name in self._hive_i:
            bee = getattr(self._hive_i, bee_name)

            if not isinstance(bee, HiveObject):
                continue

            resolved_child_bee = getattr(resolved_bee, bee_name)
            imported_namespace = dict(sockets=all_sockets, plugins=all_plugins, resolved_self=resolved_child_bee)

            bee.import_namespace(imported_namespace)

    @classmethod
    @memoize
    def _hive_get_meta_primitive(cls):
        return type("MetaHivePrimitive::{}".format(cls.__name__), (MetaHivePrimitive,), dict(_hive_object_cls=cls))

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

    def __repr__(self):
        return "[{}({})::{}]".format(self.__class__.__name__, id(self), getattr(self._hive_meta_args_frozen, 'i', None))


class MetaHivePrimitive:
    _hive_object_cls = None

    def __new__(cls, *args, **kwargs):
        self = cls._hive_object_cls(*args, **kwargs)

        if get_mode() == "immediate":
            return self.instantiate()

        else:
            return self


class HiveBuilder(object):
    """Deferred Builder for constructing Hive classes.

    Perform building once for multiple instances of the same Hive.
    """

    _builders = ()
    _declarators = ()
    _is_dyna_hive = False

    _hive_meta_args = None

    def __new__(cls, *args, **kwargs):
        args, kwargs, hive_object_cls = cls._hive_get_hive_object_cls(args, kwargs)

        # If MetaHive and not DynaHive
        if cls._declarators and not cls._is_dyna_hive:
            return hive_object_cls._hive_get_meta_primitive()

        self = hive_object_cls(*args, **kwargs)

        if get_mode() == "immediate":
            return self.instantiate()

        else:
            return self

    @classmethod
    @memoize
    def _hive_build(cls, meta_arg_values):
        """Build a HiveObject for this Hive, with appropriate Args instance

        :param kwargs: Parameter keyword arguments
        """
        hive_object_dict = {'__doc__': cls.__doc__, "_hive_parent_class": cls}
        hive_object_cls = type("{}::hive_object".format(cls.__name__), (HiveObject,), hive_object_dict)

        hive_object_cls._hive_i = internals = HiveInternals(hive_object_cls)
        hive_object_cls._hive_ex = externals = HiveExportables(hive_object_cls)
        hive_object_cls._hive_args = args = HiveArgs(hive_object_cls, "args")

        # Get frozen meta args
        frozen_meta_args = cls._hive_meta_args.freeze(meta_arg_values)
        hive_object_cls._hive_meta_args_frozen = frozen_meta_args

        is_root = get_building_hive() is None
        is_meta_hive = bool(cls._declarators)

        with hive_mode_as("build"), building_hive_as(hive_object_cls), bee_register_context() as registered_bees:
            # Invoke builder functions to build wrappers
            for builder, builder_cls in cls._builders:
                if builder_cls is not None:
                    wrapper = HiveMethodWrapper(builder_cls)
                    builder_args = wrapper, internals, externals, args

                else:
                    builder_args = internals, externals, args

                if is_meta_hive:
                    builder_args = builder_args + (frozen_meta_args,)

                builder(*builder_args)

            # Importing
            child_plugins = {}
            child_sockets = {}

            child_plugin_names = {}
            child_socket_names = {}

            child_hives = set()

            # Find plugins and sockets
            for bee_name in externals:
                bee = getattr(externals, bee_name)

                if bee.implements(Plugin) and bee.identifier is not None:
                    child_plugins[bee.identifier] = bee
                    child_plugin_names[bee.identifier] = bee_name

                elif bee.implements(Socket) and bee.identifier is not None:
                    child_sockets[bee.identifier] = bee
                    child_socket_names[bee.identifier] = bee_name

                elif isinstance(bee, HiveObject):
                    child_hives.add(bee)

            # Find internal hives
            for bee_name in internals:
                bee = getattr(internals, bee_name)

                if isinstance(bee, HiveObject):
                    child_hives.add(bee)

            # Save namespace of hive
            hive_object_cls._hive_namespace = dict(plugins=child_plugins,
                                                   sockets=child_sockets,
                                                   plugin_names=child_plugin_names,
                                                   socket_names=child_socket_names)

            # Automatically connect plugins and sockets
            if is_root:
                for bee in child_hives:
                    # Create connections to sockets and plugins
                    namespace = dict(plugins=child_plugins, sockets=child_sockets, resolved_self=bee)
                    bee.import_namespace(namespace)

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
        run_hive_class_dict = {"__doc__": cls.__doc__}

        # For internal bees
        for bee_name in internals:
            bee = getattr(internals, bee_name)

            private_bee_name = "_{}".format(bee_name)

            # If the bee requires a property interface, build a property
            if isinstance(bee, Stateful):
                run_hive_class_dict[private_bee_name] = property(bee._hive_stateful_getter, bee._hive_stateful_setter)

        # For external bees
        for bee_name in externals:
            bee = getattr(externals, bee_name)

            # If the bee requires a property interface, build a property
            if isinstance(bee, Stateful):
                run_hive_class_dict[bee_name] = property(bee._hive_stateful_getter, bee._hive_stateful_setter)

        hive_object_cls._hive_runtime_class = type("{}::run_hive".format(hive_object_cls.__name__), (RuntimeHive,),
                                                   run_hive_class_dict)
        return hive_object_cls

    @classmethod
    def _hive_build_meta_args_wrapper(cls):
        cls._hive_meta_args = args_wrapper = HiveArgs(cls, "meta_args")

        # Execute declarators
        with hive_mode_as("declare"):
            for declarator in cls._declarators:
                declarator(args_wrapper)

    @classmethod
    def _hive_get_hive_object_cls(cls, args, kwargs):
        """Find appropriate HiveObject for argument values

        Extract meta args from arguments and return remainder
        """
        if cls._hive_meta_args is None:
            cls._hive_build_meta_args_wrapper()

        # Map keyword arguments to parameters, return remaining arguments
        args, kwargs, meta_arg_values = cls._hive_meta_args.extract_from_args(args, kwargs)

        # If a new combination of parameters is provided
        return args, kwargs, cls._hive_build(meta_arg_values)

    @classmethod
    def extend(cls, name, builder, builder_cls=None, declarator=None, is_dyna_hive=False):
        """Extend HiveObject with an additional builder (and builder class)

        :param name: name of new hive class
        :param builder: optional function used to build hive
        :param builder_cls: optional Python class to bind to hive
        :param declarator: optional declarator to establish parameters
        """
        if builder_cls is not None:
            assert issubclass(builder_cls, object), "cls must be a new-style Python class, e.g. class SomeHive(object): ..."

        # Add new builder function
        builders = cls._builders + ((builder, builder_cls),)

        # Add new declarator
        if declarator is not None:
            declarators = cls._declarators + (declarator,)

        else:
            declarators = cls._declarators

        # Build docstring
        docstring = "\n".join([f.__doc__ for f, c in builders if f.__doc__ is not None])

        if is_dyna_hive:
            assert declarators, "cannot set is_dyna_hive to True without declarators"

        class_dict = {
            "__doc__": docstring,
            "_builders": builders,
            "_declarators": declarators,
            "_hive_meta_args": None,
            "_is_dyna_hive": is_dyna_hive,
        }

        return type(name, (cls,), class_dict)


# TODO options for namespaces (old frame/hive distinction)
def hive(name, builder, cls=None):
    if cls is not None:
        assert issubclass(cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

    return HiveBuilder.extend(name, builder, cls)


def dyna_hive(name, builder, declarator, cls=None):
    if cls is not None:
        assert issubclass(cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

    return HiveBuilder.extend(name, builder, cls, declarator=declarator, is_dyna_hive=True)


def meta_hive(name, builder, declarator, cls=None):
    if cls is not None:
        assert issubclass(cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

    return HiveBuilder.extend(name, builder, cls, declarator=declarator)






# Metahive returns a primitive
# Dynahive is a metahive which instantiates immediately, no args wrapper - but instantiate build class with unused parameters
# Declare Meta Args
#   -> Parse meta args
#       -> Invoke builder
# If no declarator, is not meta

def build():
    if meta_args is None:
        declare_meta_args()

    declared_params = meta_args.parse(args, kwargs)
    hive_obj = hive_objs[declared_params]

    if hive_obj is None:
        frozen_meta_args = meta_args.freeze(declared_params)

        if is_meta:
            args = ...
            hive_obj = build_hive_obj(cls, i, ex, frozen_meta_args, args)
        elif is_dyna:
            hive_obj = build_hive_obj(cls, i, ex, frozen_meta_args)
        else:
            hive_obj = build_hive_obj(cls, i, ex, args)

