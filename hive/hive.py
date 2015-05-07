from .classes import HiveInternals, HiveExportables, HiveArgs, ResolveBee, Method
from .mixins import *
from .manager import bee_register_context, get_mode, hive_mode_as, get_building_hive, building_hive_as, run_hive_as, \
    memoize
from .tuple_type import tuple_type, types_match

from itertools import product
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


def is_method(func):
    """Test if value is a callable method.

    Python 3 disposes of this notion, so we only need check if it is callable.
    """
    if hasattr(func, "im_class"):
        return True

    return inspect.isfunction(func)


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
        raise AttributeError("HiveMethodWrapper of class '%s' is read-only" % self._cls.__name__)


class Generic(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        return str(self.__dict__)


def find_connection_candidates(sources, targets, require_types=True):
    """Finds appropriate connections between ConnectionSources and ConnectionTargets

    :param sources: connection sources
    :param targets: connection targets
    :param require_types: require type definitions to be declared
    """
    candidates = []

    for source_candidate, target_candidate in product(sources, targets):
        source_data_type = source_candidate.data_type
        target_data_type = target_candidate.data_type

        if require_types and (not source_data_type or not target_data_type):
            continue

        if not types_match(source_data_type, target_data_type):
            continue

        candidates.append((source_candidate, target_candidate))

    return candidates


def connect_hives(source, target):    
    assert isinstance(source, RuntimeHive) == isinstance(target, RuntimeHive)
    if isinstance(source, RuntimeHive):
        source_hive_object = source._hive_object
        target_hive_object = target._hive_object

    else:
        source_hive_object = source
        target_hive_object = target

    source_externals = source_hive_object._hive_parent_class._hive_ex
    target_externals = target_hive_object._hive_parent_class._hive_ex

    # Find source hive ConnectSources
    connect_sources = []
    for bee_name in dir(source_externals):
        bee = getattr(source_externals, bee_name)
        exported_bee = bee.export()

        if not exported_bee.implements(ConnectSource): 
            continue

        source_data_type = tuple_type(exported_bee.data_type)
        candidate = Generic(attrib=bee_name, data_type=source_data_type, bee=exported_bee)
        connect_sources.append(candidate)

    # Find target hive ConnectSources
    connect_targets = []
    for bee_name in dir(target_externals):
        bee = getattr(target_externals, bee_name)
        exported_bee = bee.export()

        if not exported_bee.implements(ConnectTarget): 
            continue

        target_data_type = tuple_type(exported_bee.data_type)
        candidate = Generic(attrib=bee_name, data_type=target_data_type, bee=exported_bee)
        connect_targets.append(candidate)
    
    # First try: match candidates with named data_type
    candidates = find_connection_candidates(connect_sources, connect_targets)

    if not candidates:
        candidates = find_connection_candidates(connect_sources, connect_targets, require_types=False)
      
    if not candidates:
        # TODO: nicer error message
        raise TypeError("No matching connections found")

    elif len(candidates) > 1:
        candidate_names = [(a.attrib, b.attrib) for a, b in candidates]
        # TODO: nicer error message
        raise TypeError("Multiple matches: %s" % candidate_names)

    if isinstance(source, RuntimeHive):
        source_candidate = getattr(source, candidates[0][0].attrib)
        target_candidate = getattr(target, candidates[0][1].attrib)

    else:
        source_candidate = candidates[0][0].bee
        target_candidate = candidates[0][1].bee
    
    return source_candidate, target_candidate


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

            building_hive = hive_object._hive_parent_class
            with building_hive_as(building_hive), hive_mode_as("build"):
                # Add external bees
                bees = []
                external_bees = building_hive._hive_ex

                for bee_name in dir(external_bees):
                    bee = getattr(external_bees, bee_name)
                    exported_bee = bee.export()

                    # TODO: nice exception reporting
                    instance = exported_bee.getinstance(self._hive_object)

                    if isinstance(instance, Bindable):
                        instance = instance.bind(self)

                    bees.append((bee_name, instance))

                # Add internal bees that are hives, Callable or Stateful
                internal_bees = building_hive._hive_i
                for bee_name in dir(internal_bees):
                    bee = getattr(internal_bees, bee_name)
                    private_name = "_" + bee_name

                    # Protected attribute starting with _hive
                    assert not hasattr(self, private_name), private_name

                    # TODO: nice exception reporting
                    instance = bee.getinstance(self._hive_object)
                    if isinstance(instance, Bindable):
                        instance = instance.bind(self)
                        if instance is None:
                            continue

                        instance.parent = self

                    if isinstance(bee, HiveObject) or bee.implements(Callable) or bee.implements(Stateful):
                        bees.append((private_name, instance))

                bees.sort(key=bee_sort_key)

                for bee_name, instance in bees:
                    if isinstance(instance, Stateful):
                        continue

                    instance._hive_bee_name = self._hive_bee_name + (bee_name,)
                    self._hive_bee_instances[bee_name] = instance
                    self._bee_names.append(bee_name)
                    setattr(self, bee_name, instance)

    def _hive_trigger_source(self, target_func):
        source_name = self._hive_object._find_trigger_source()
        instance = self._hive_bee_instances[source_name]
        return instance._hive_trigger_source(target_func)

    def _hive_trigger_target(self):
        target_name = self._hive_object._find_trigger_target()
        instance = self._hive_bee_instances[target_name]
        return instance._hive_trigger_target()

    def _find_connect_source(self, target):
        source_name = self._hive_object._find_connect_source(target)
        return getattr(self, source_name)

    def _find_connect_target(self, source):
        target_name = self._hive_object._find_connect_target(source)
        return getattr(self, target_name)
      
    def implements(self, cls):
        return isinstance(self, cls)
      
    def __dir__(self):
        return self._bee_names


class HiveObject(Exportable, ConnectSourceDerived, ConnectTargetDerived, TriggerSource, TriggerTarget):
    """Built Hive class responsible for creating new Hive instances.

    All bees defined with the builder functions are memoized and cached for faster instantiation
    """

    _hive_parent_class = None
    _hive_runtime_class = None
    _hive_bee_name = tuple()

    export_only = False

    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        self._hive_cls = get_building_hive()
        
        # TODO: filter args and kwargs based on _hive_args and _hive_hive_kwargs
        
        #args to make parameter dict for bee.parameter
        self._hive_param_args = args #for now
        self._hive_param_kwargs = kwargs #for now
        
        # TODO: instantiate parameter dict and send it to the resolve manager

        #args to instantiate builderclass instances
        self._hive_builder_args = args #for now
        self._hive_builder_kwargs = kwargs #for now
            
        #check calling signature of builderclass.__init__
        init_plus_args = (None,) + self._hive_builder_args

        for builder, builder_cls in self._hive_parent_class._builders:
            if builder_cls is not None and hasattr(inspect, "getcallargs") and inspect.isfunction(builder_cls.__init__):
                try:
                    inspect.getcallargs(builder_cls.__init__, *init_plus_args, **self._hive_builder_kwargs)

                except TypeError as err:
                    raise TypeError("{}.{}".format(builder_cls.__name__, err.args[0]))

        with hive_mode_as("build"):
            external_bees = self._hive_parent_class._hive_ex
            for bee_name in dir(external_bees):
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
    
    @classmethod
    def _find_trigger_target(cls):
        """Find name of single external bee that supported TriggerTarget interface.

        Raise TypeError if such a condition cannot be met
        """
        external_bees = cls._hive_parent_class._hive_ex
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

    def _get_trigger_target(self):
        """Return single external bee that supported TriggerTarget interface"""
        trigger_name = self._find_trigger_target()
        return getattr(self, trigger_name)
        
    @classmethod
    def _find_trigger_source(cls):
        """Find name of single external bee that supported TriggerSource interface.

        Raise TypeError if such a condition cannot be met
        """
        external_bees = cls._hive_parent_class._hive_ex
        trigger_sources = []

        for bee_name in dir(external_bees):
            bee = getattr(external_bees, bee_name)
            exported_bee = bee.export()

            if isinstance(exported_bee, TriggerSource):
                trigger_sources.append(bee_name)

        if not trigger_sources:
            raise TypeError("No TriggerSources in %s" % cls)

        elif len(trigger_sources) > 1:
            raise TypeError("Multiple TriggerSources in %s: %s" % (cls, trigger_sources))

        return trigger_sources[0]

    def _get_trigger_source(self):
        """Return single external bee that supported TriggerSource interface"""
        attr = self._find_trigger_source()
        return getattr(self, attr)    

    @classmethod
    def _find_connect_source(cls, target):
        assert target.implements(ConnectTarget)
        external_bees = cls._hive_parent_class._hive_ex
        target_data_type = tuple_type(target.data_type)

        connect_sources = []
        for bee_name in dir(external_bees):
            bee = getattr(external_bees, bee_name)
            exported_bee = bee.export()
            if not exported_bee.implements(ConnectSource):
                continue

            source_data_type = tuple_type(exported_bee.data_type)
            if not types_match(source_data_type, target_data_type):
                pass

            connect_sources.append(bee_name)

        if not connect_sources:
            raise TypeError("No matching connections found") #TODO: nicer error message

        elif len(connect_sources) > 1:
            raise TypeError("Multiple matches: %s" % connect_sources) #TODO: nicer error message

        return connect_sources[0]
            
    @classmethod
    def _find_connect_target(cls, source):
        assert source.implements(ConnectSource)
        external_bees = cls._hive_parent_class._hive_ex
        source_data_type = tuple_type(source.data_type)

        connect_targets = []
        for bee_name in dir(external_bees):
            bee = getattr(external_bees, bee_name)
            exported_bee = bee.export()
            if not exported_bee.implements(ConnectTarget): 
                continue

            target_data_type = tuple_type(exported_bee.data_type)
            if not types_match(source_data_type, target_data_type):
                pass

            connect_targets.append(bee_name)
        
        if not connect_targets:
            raise TypeError("No matching connections found") #TODO: nicer error message

        elif len(connect_targets) > 1:            
            raise TypeError("Multiple matches: %s" % connect_targets) #TODO: nicer error message

        return connect_targets[0]
      
    def export(self):
        return self


class HiveBuilder(object):
    """Deferred Builder for constructing Hive classes.

    Perform building once for multiple instances of the same Hive.
    """

    _builders = ()
    _hive_built = False
    _hive_i = None
    _hive_ex = None
    _hive_args = None    
    _hive_hive_kwargs = False
    _hive_object_cls = None

    def __new__(cls, *args, **kwargs):        
        if not cls._hive_built:
            cls._hive_build()

        hive_object_cls = cls._hive_object_cls
        self = hive_object_cls(*args, **kwargs)

        if get_mode() == "immediate":
            return self.instantiate()

        else:
            return self

    @classmethod
    def extend(cls, name, builder, builder_cls=None, hive_kwargs=False):
        if builder_cls is not None:
            assert issubclass(builder_cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

        builders = cls._builders + ((builder, builder_cls),)
        class_dict = {
            "_builders": builders,
            "_hive_hive_kwargs": hive_kwargs,
        }

        return type(name, (cls,), class_dict)
         
    @classmethod
    def _hive_build(cls):
        assert not cls._hive_built
        cls._hive_build_methods()

        # TODO: auto-remove connections/triggers for which the source/target has been deleted
        # TODO: sockets and plugins, take options into account for namespaces
        run_hive_class_dict = {}
        hive_externals = cls._hive_ex

        for bee_name in dir(hive_externals):
            bee = getattr(hive_externals, bee_name)

            # If the bee requires a property interface, build a property
            if isinstance(bee, Stateful):
                run_hive_class_dict[bee_name] = property(bee._hive_stateful_getter, bee._hive_stateful_setter)

        class_dict = {
            "_hive_runtime_class": type("{}::run_hive".format(cls.__name__), (RuntimeHive,), run_hive_class_dict),
            "_hive_parent_class": cls,
        }

        cls._hive_object_cls = type(cls.__name__+"{}::hive_object".format(cls.__name__), (HiveObject,), class_dict)
        cls._hive_built = True

    @classmethod
    def _hive_build_methods(cls):
        assert not cls._hive_built

        with hive_mode_as("build"), building_hive_as(cls), bee_register_context() as registered_bees:

            cls._hive_i = HiveInternals(cls)
            cls._hive_ex = HiveExportables(cls)
            cls._hive_args = HiveArgs(cls)

            for builder, builder_cls in cls._builders:
                if builder_cls is not None:
                    wrapper = HiveMethodWrapper(builder_cls)
                    builder(wrapper, cls._hive_i, cls._hive_ex, cls._hive_args)

                else:
                    builder(cls._hive_i, cls._hive_ex, cls._hive_args)

        # Find anonymous bees
        anonymous_bees = set(registered_bees)

        # Find any anonymous bees which are held on object
        internal_bees = cls._hive_i
        for bee_name in dir(internal_bees):
            bee = getattr(internal_bees, bee_name)

            if bee in anonymous_bees:
                anonymous_bees.remove(bee)

        # Save anonymous bees to internal wrapper, with unique names
        for bee in registered_bees:
            if bee not in anonymous_bees:
                continue

            # Find unique name for bee
            while True:
                bee_name = next(it_generate_bee_name)
                if not hasattr(internal_bees, bee_name):
                    break

            setattr(internal_bees, bee_name, bee)

        # Write the name of all bees to their instances
        for bee_name in dir(internal_bees):
            bee = getattr(internal_bees, bee_name)
            bee._hive_bee_name = (bee_name,)


# TODO options for namespaces (old frame/hive distinction)
def hive(name, builder, cls=None, hive_kwargs=False):
    if cls is not None:
        assert issubclass(cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

    return HiveBuilder.extend(name, builder, cls, hive_kwargs)