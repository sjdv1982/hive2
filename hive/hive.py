from .mixins import *
from .classes import HiveInternals, HiveExportables, HiveArgs, ResolveBee, Method
from . import get_mode, set_mode, get_building_hive, set_building_hive, get_runhive, set_runhive
from . import manager

import inspect


def generate_beename():
    # TODO python 3 doesn't support xrange
    i = 0
    while True:
        i += 1
        yield "bee {}".format(i)


it_generate_beename = generate_beename()


def beekeyfunc(item):
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

    def __init__(self, cls):
        object.__setattr__(self, "_cls", cls)

    def __getattr__(self, attr):
        value = getattr(self._cls, attr)

        if inspect.ismethod(value):
            return Method(value)

        else:
            return value

    def __setattr__(self, attr):
        raise AttributeError("HiveMethodWrapper of class '%s' is read-only" % self._cls.__name__)


class runhive(ConnectSource, ConnectTarget, TriggerSource, TriggerTarget):

    def __init__(self, hive_object, builders):
        self._hive_bee_name = hive_object._hive_bee_name
        self._hive_object = hive_object
        self._hive_buildclass_instances = {}
        self._hive_bee_instances = {}
        self._attrs = ["_drones"]
        self._drones = []

        manager.register_runhive(self) 
        
        current_run_hive = get_runhive()
        set_runhive(self)

        try:
            for builder, bcls in builders:
                args = self._hive_object._hive_builder_args
                kwargs = self._hive_object._hive_builder_kwargs

                if bcls is not None:
                    assert id(bcls) not in self._hive_buildclass_instances, bcls
                    buildclass_instance = bcls.__new__(bcls)
                    self._hive_buildclass_instances[id(bcls)] = buildclass_instance
                    self._drones.append(buildclass_instance)
                    bcls.__init__(buildclass_instance, *args, **kwargs)                
        finally:
            set_runhive(current_run_hive)
            
        m = get_mode()
        bh = get_building_hive()        
        set_mode("build")
        set_building_hive(self._hive_object._hive_parent_class)
        set_runhive(self)

        try:            
            bees = []
                        
            #add ex bees
            hive_externals = self._hive_object._hive_parent_class._hive_ex

            for name in dir(hive_externals):
                bee = getattr(hive_externals, name)
                bee = bee.export()
                # TODO: nice exception reporting
                instance = bee.getinstance(self._hive_object)

                if isinstance(instance, Bindable):
                    instance = instance.bind(self)

                bees.append((name, instance))
            
            #add i bees that are hives, Callable or Stateful
            hive_internals = self._hive_object._hive_parent_class._hive_i
            for name in hive_internals._attrs:
                bee = getattr(hive_internals, name)
                private_name = "_" + name

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
            
            bees.sort(key=beekeyfunc)
            
            for name, instance in bees:
                if isinstance(instance, Stateful):
                    continue

                instance._hive_bee_name = self._hive_bee_name + (name,)
                self._hive_bee_instances[name] = instance
                self._attrs.append(name)
                setattr(self, name, instance)
                    
        finally:
            set_mode(m)
            set_building_hive(bh)
            set_runhive(current_run_hive)

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
    _hive_parent_class = None
    _hive_run_class = None
    _hive_bee_name = tuple()

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
            if builder_cls is not None and hasattr(inspect, "getcallargs") and inspect.ismethod(builder_cls.__init__):
                try:
                    inspect.getcallargs(builder_cls.__init__, *init_plus_args, **self._hive_builder_kwargs)

                except TypeError as err:
                    raise TypeError("{}.{}".format(builder_cls.__name__, err.args[0]))
        
        current_build_mode = get_mode()
        set_mode("build")

        try:
            for attr in dir(self._hive_parent_class._hive_ex):
                exportable = getattr(self._hive_parent_class._hive_ex, attr)
                target = exportable.export()
                resolve_bee = ResolveBee(target, self)
                setattr(self, attr, resolve_bee)

        finally:
            set_mode(current_build_mode)

        return self
                
    @manager.getinstance    
    def getinstance(self, parenthiveobject): 
        return self.instantiate()
    
    def instantiate(self):        
        manager.register_hiveobject(self)            
        return self._hive_run_class(self, self._hive_parent_class._builders)
    
    @classmethod
    def search_trigger_target(cls):
        ex = cls._hive_parent_class._hive_ex
        triggertargets = []

        for attr in dir(ex):
            bee = getattr(ex, attr)
            exbee = bee.export()
            if isinstance(exbee, TriggerTarget):
                triggertargets.append(attr)

        if len(triggertargets) == 0:
            raise TypeError("No TriggerTargets in %s" % cls)

        elif len(triggertargets) > 1:
            raise TypeError("Multiple TriggerTargets in %s: %s" % (cls, triggertargets))

        return triggertargets[0]

    def get_trigger_target(self):
        attr = self.search_trigger_target()
        return getattr(self, attr)
        
    @classmethod
    def search_trigger_source(cls):
        ex = cls._hive_parent_class._hive_ex
        triggersources = []

        for attr in dir(ex):
            bee = getattr(ex, attr)
            exbee = bee.export()

            if isinstance(exbee, TriggerSource):
                triggersources.append(attr)

        if len(triggersources) == 0:
            raise TypeError("No TriggerSources in %s" % cls)

        elif len(triggersources) > 1:
            raise TypeError("Multiple TriggerSources in %s: %s" % (cls, triggersources))

        return triggersources[0]

    def get_trigger_source(self):
        attr = self.search_trigger_source()
        return getattr(self, attr)    
    
    def export(self):
        return self


class Hive(object):
    _builders = ()
    _hive_built = False
    _hive_i = None
    _hive_ex = None
    _hive_args = None    
    _hive_hive_kwargs = False
    _hive_object_class = None

    def __new__(cls, *args, **kwargs):        
        if not cls._hive_built:
            cls._hive_build()

        hive_object_cls = cls._hive_object_cls
        self = hive_object_cls.__new__(hive_object_cls, *args, **kwargs)

        if get_mode() == "immediate":
            return self.instantiate()

        else:
            return self
    
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
        hive_internals = cls._hive_i
        for bee_name in dir(hive_internals):
            bee = getattr(hive_internals, bee_name)

            if bee in anonymous_bees:
                anonymous_bees.remove(bee)

        # Save anonymous bees to internal wrapper, with unique names
        for bee in bees:
            if bee not in anonymous_bees:
                continue

            # Find unique name for bee
            while True:
                bee_name = next(it_generate_beename)
                if not hasattr(hive_internals, bee_name):
                    break

            setattr(hive_internals, bee_name, bee)

        # Write the name of all bees to their instances
        for bee_name in dir(hive_internals):
            bee = getattr(hive_internals, bee_name)
            bee._hive_bee_name = (bee_name,)
         
    @classmethod
    def _hive_build(cls):
        assert not cls._hive_built
        cls._hive_build_methods()

        # TODO: auto-remove connections/triggers for which the source/target has been deleted
        # TODO: sockets and plugins, take options into account for namespacing
        run_hive_class_dict = {}
        hive_externals = cls._hive_ex

        for attr in dir(hive_externals):
            bee = getattr(hive_externals, attr)

            # If the bee requires a property interface, build a property
            if isinstance(bee, Stateful):
                run_hive_class_dict[attr] = property(bee._hive_stateful_getter, bee._hive_stateful_setter)

        class_dict = {
            "_hive_run_class": type("{}::runhive".format(cls.__name__), (runhive,), run_hive_class_dict),
            "_hive_parent_class": cls,
        }

        cls._hive_object_class = type(cls.__name__+"{}::hiveobject".format(cls.__name__), (HiveObject,), class_dict)
        cls._hive_built = True 
     
    @classmethod
    def extend(hivebase, name, builder, cls=None, hive_kwargs=False):
        if cls is not None:
            assert issubclass(cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

        builders = hivebase._builders + ((builder, cls),)
        class_dict = {
            "_builders": builders,
            "_hive_hive_kwargs": hive_kwargs,
        }

        return type(name, (hivebase,), class_dict)


# TODO options for namespacing (old frame/hive distinction)
def hive(name, builder, cls=None, hive_kwargs=False):
    if cls is not None:
        assert issubclass(cls, object), "cls must be a new-style Python class, e.g. class cls(object): ..."

    return Hive.extend(name, builder, cls, hive_kwargs)