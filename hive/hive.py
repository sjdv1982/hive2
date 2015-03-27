from .mixins import *
from .classes import HiveInternals, HiveExportables, HiveArgs, ResolveBee, Method
from . import get_mode, set_mode, get_building_hive, set_building_hive, get_run_hive, set_run_hive
from . import manager

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
        print(b)
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


class RuntimeHive(ConnectSource, ConnectTarget, TriggerSource, TriggerTarget):
    """Unique Hive instance that is created at runtime for a Hive object.

    Lightweight instantiation is supported through caching performed by the HiveObject instance.
    """

    def __init__(self, hive_object, builders):
        self._hive_bee_name = hive_object._hive_bee_name
        self._hive_object = hive_object
        self._hive_build_class_instances = {}
        self._hive_bee_instances = {}
        self._attrs = ["_drones"]
        self._drones = []

        manager.register_run_hive(self)
        
        current_run_hive = get_run_hive()
        set_run_hive(self)

        try:
            for builder, builder_cls in builders:
                args = self._hive_object._hive_builder_args
                kwargs = self._hive_object._hive_builder_kwargs

                if builder_cls is not None:
                    assert builder_cls not in self._hive_build_class_instances, builder_cls

                    # Do not initialise instance yet
                    build_class_instance = builder_cls.__new__(builder_cls)

                    self._hive_build_class_instances[builder_cls] = build_class_instance
                    self._drones.append(build_class_instance)

                    build_class_instance.__init__(*args, **kwargs)
        finally:
            set_run_hive(current_run_hive)

        # To restore state later on
        current_mode = get_mode()
        current_building_hive = get_building_hive()

        set_mode("build")
        set_building_hive(self._hive_object._hive_parent_class)
        set_run_hive(self)

        try:            
            bees = []
                        
            # Add external bees
            hive_externals = self._hive_object._hive_parent_class._hive_ex

            for bee_name in dir(hive_externals):
                bee = getattr(hive_externals, bee_name)
                bee = bee.export()
                # TODO: nice exception reporting
                instance = bee.getinstance(self._hive_object)

                if isinstance(instance, Bindable):
                    instance = instance.bind(self)

                bees.append((bee_name, instance))
            
            # Add internal bees that are hives, Callable or Stateful
            internal_bees = self._hive_object._hive_parent_class._hive_i
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
                self._attrs.append(bee_name)
                setattr(self, bee_name, instance)
                    
        finally:
            set_mode(current_mode)
            set_building_hive(current_building_hive)
            set_run_hive(current_run_hive)

    def _hive_trigger_source(self, target_func):
        attr = self._hive_object.search_trigger_source()        
        instance = self._hive_bee_instances[attr]
        return instance._hive_trigger_source(target_func)

    def _hive_trigger_target(self):
        attr = self._hive_object.search_trigger_target()
        instance = self._hive_bee_instances[attr]
        return instance._hive_trigger_target()

    def __dir__(self):
        return self._attrs


class HiveObject(Exportable, ConnectSource, ConnectTarget, TriggerSource, TriggerTarget):
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
        
        current_build_mode = get_mode()
        set_mode("build")

        try:
            external_bees = self._hive_parent_class._hive_ex
            for bee_name in dir(external_bees):
                exportable = getattr(external_bees, bee_name)
                target = exportable.export()
                resolve_bee = ResolveBee(target, self)
                setattr(self, bee_name, resolve_bee)

        finally:
            set_mode(current_build_mode)

        return self
                
    @manager.getinstance    
    def getinstance(self, parent_hive_object):
        return self.instantiate()
    
    def instantiate(self):
        """Return an instance of the runtime Hive for this Hive object."""
        manager.register_hive_object(self)
        return self._hive_runtime_class(self, self._hive_parent_class._builders)
    
    @classmethod
    def search_trigger_target(cls):
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

    def get_trigger_target(self):
        attr = self.search_trigger_target()
        return getattr(self, attr)
        
    @classmethod
    def search_trigger_source(cls):
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

    def get_trigger_source(self):
        attr = self.search_trigger_source()
        return getattr(self, attr)    
    
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

        # Original state
        current_build_mode = get_mode()
        current_build_hive = get_building_hive()

        set_mode("build")
        set_building_hive(cls)
        manager.register_bee_push()

        try:
            cls._hive_i = HiveInternals(cls)
            cls._hive_ex = HiveExportables(cls)
            cls._hive_args = HiveArgs(cls)

            for builder, builder_cls in cls._builders:
                if builder_cls is not None:
                    wrapper = HiveMethodWrapper(builder_cls)
                    builder(wrapper, cls._hive_i, cls._hive_ex, cls._hive_args)

                else:
                    builder(cls._hive_i, cls._hive_ex, cls._hive_args)

        finally:
            set_mode(current_build_mode)
            set_building_hive(current_build_hive)
            bees = manager.register_bee_pop()

        # Find anonymous bees
        anonymous_bees = set(bees)

        # Find any anonymous bees which are held on object
        internal_bees = cls._hive_i
        for bee_name in dir(internal_bees):
            bee = getattr(internal_bees, bee_name)

            if bee in anonymous_bees:
                anonymous_bees.remove(bee)

        # Save anonymous bees to internal wrapper, with unique names
        for bee in bees:
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