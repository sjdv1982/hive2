from .mixins import *
from .classes import HiveInternals, HiveExportables, HiveArgs, HiveBee, CrossBee, Method
from . import get_mode, set_mode, get_building_hive, set_building_hive, get_runhive, set_runhive
from . import manager
import functools

def generate_beename():
  for n in xrange(999999999):
    yield "bee" + str(n+1)
it_generate_beename = generate_beename()

import inspect 
 
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
    v = getattr(self._cls, attr)
    if hasattr(v, "im_class"):
      return Method(v)
    else:
      return v
  def __setattr__(self, attr):
    raise AttributeError("HiveMethodWrapper of class '%s' is read-only" % self._cls.__name__)

class runhive(ConnectSource, ConnectTarget, TriggerSource, TriggerTarget):  
  def __init__(self, hive_object, builders):
    self._hive_beename =  hive_object._hive_beename
    self._hive_object = hive_object
    self._hive_buildclass_instances = {}
    self._hive_bee_instances = {}
    self._attrs = ["_drones"]
    self._drones = []
    manager.register_runhive(self) 
    
    rh = get_runhive()
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
      set_runhive(rh)
      
    m = get_mode()
    bh = get_building_hive()    
    set_mode("build")
    set_building_hive(self._hive_object._hive_parentclass)
    set_runhive(self)
    try:      
      bees = []
            
      #add ex bees
      ex = self._hive_object._hive_parentclass._hive_ex
      for attr in dir(ex):
        bee = getattr(ex, attr)
        bee = bee.export()
        instance = bee.getinstance(self._hive_object) #TODO: nice exception reporting
        if isinstance(instance, Bindable):
          instance = instance.bind(self)
        bees.append((attr, instance))
      
      #add i bees that are hives, Callable or Stateful
      i = self._hive_object._hive_parentclass._hive_i
      for attr in i._attrs:
        bee = getattr(i, attr)
        attr2 = "_" + attr
        assert not hasattr(self, attr2), attr2 #protected attribute starting with _hive
        instance = bee.getinstance(self._hive_object) #TODO: nice exception reporting          
        if isinstance(instance, Bindable):          
          instance = instance.bind(self)
          if instance is None: 
            continue
          instance.parent = self          
        if isinstance(bee, HiveObject) or bee.implements(Callable) or bee.implements(Stateful):
          bees.append((attr2, instance))
      
      bees.sort(key=beekeyfunc)
      
      for beename, instance in bees:        
        if isinstance(instance, Stateful):
          continue        
        instance._hive_beename = self._hive_beename + (beename,)
        self._hive_bee_instances[beename] = instance          
        self._attrs.append(beename)
        setattr(self, beename, instance)
          
    finally:
      set_mode(m)
      set_building_hive(bh)  
      set_runhive(rh)
  def _hive_trigger_source(self, targetfunc):
    attr = self._hive_object.search_trigger_source()    
    instance = self._hive_bee_instances[attr]
    return instance._hive_trigger_source(targetfunc)
  def _hive_trigger_target(self):
    attr = self._hive_object.search_trigger_target()
    instance = self._hive_bee_instances[attr]
    return instance._hive_trigger_target()
  def __dir__(self):
    return self._attrs
  
class HiveObject(Exportable, ConnectSource, ConnectTarget, TriggerSource, TriggerTarget):
  _hive_parentclass = None
  _hive_runclass = None
  _hive_beename = tuple()
  def __new__(cls, *args, **kwargs):
    self = object.__new__(cls)
    self._hivecls = get_building_hive()
    
    #TODO: filter args and kwargs based on _hive_args and _hive_hivekwargs
    
    #args to make parameter dict for bee.parameter
    self._hive_param_args = args #for now
    self._hive_param_kwargs = kwargs #for now
    
    #TODO: instantiate parameter dict and send it to the resolve manager

    #args to instantiate builderclass instances
    self._hive_builder_args = args #for now
    self._hive_builder_kwargs = kwargs #for now
      
    #check calling signature of builderclass.__init__
    init_plus_args = (None,) + self._hive_builder_args
    for builder, bcls in self._hive_parentclass._builders:
      if bcls is not None and hasattr(inspect, "getcallargs") and inspect.ismethod(bcls.__init__):
        try:
          inspect.getcallargs(bcls.__init__, *init_plus_args, **self._hive_builder_kwargs)
        except TypeError as e:
          raise TypeError(bcls.__name__+"."+e.args[0])
    
    m = get_mode()
    set_mode("build")
    for attr in dir(self._hive_parentclass._hive_ex):      
      exportable = getattr(self._hive_parentclass._hive_ex, attr)
      target = exportable.export()
      crossbee = CrossBee(target, self)
      setattr(self, attr, crossbee)
    set_mode(m)
    return self
        
  @manager.getinstance  
  def getinstance(self, parenthiveobject): 
    return self.instantiate()
  
  def instantiate(self):    
    manager.register_hiveobject(self)      
    return self._hive_runclass(self, self._hive_parentclass._builders)
  
  @classmethod
  def search_trigger_target(cls):
    ex = cls._hive_parentclass._hive_ex
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
    ex = cls._hive_parentclass._hive_ex
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
  _hive_hivekwargs = False
  _hive_objectclass = None
  def __new__(cls, *args, **kwargs):    
    if not cls._hive_built:
      cls._hive_build()
    self = cls._hive_objectclass.__new__(cls._hive_objectclass, *args, **kwargs)         
    if get_mode() == "immediate":
      return self.instantiate()
    else:
      return self
  
  @classmethod
  def _hive_build_methods(cls):
    assert not cls._hive_built 
    m = get_mode()
    bh = get_building_hive()
    set_mode("build")
    set_building_hive(cls)
    manager.register_bee_push()
    try:
      cls._hive_i = HiveInternals(cls)
      cls._hive_ex = HiveExportables(cls)
      cls._hive_args = HiveArgs(cls)
      for builder, bcls in cls._builders:
        if bcls is not None:
          bcls_wrapper = HiveMethodWrapper(bcls)
          builder(bcls_wrapper, cls._hive_i, cls._hive_ex, cls._hive_args)
        else:
          builder(cls._hive_i, cls._hive_ex, cls._hive_args)
    finally:
      set_mode(m)
      set_building_hive(bh)
      bees = manager.register_bee_pop()
        
    #look for registered bees that are not in i (e.g. connect and trigger)
    beesdict = {}
    for b in bees:
      beesdict[id(b)] = b
    i = cls._hive_i 
    for attr in dir(i):
      b = id(getattr(i, attr))
      if b in beesdict:
        beesdict.pop(b)
    bees = [b for b in bees if id(b) in beesdict]
    for bee in bees:
      while 1:
        beename = it_generate_beename.next()
        if not hasattr(i, beename): break
      setattr(i, beename, bee)
   
    for attr in dir(i):
      b = getattr(i, attr)
      b._hive_beename = (attr,)
     
  @classmethod
  def _hive_build(cls):
    assert not cls._hive_built
    cls._hive_build_methods() 
    #TODO: auto-remove connections/triggers for which the source/target has been deleted
    #TODO: sockets and plugins, take options into account for namespacing
    runhive_classdict = {}
    ex = cls._hive_ex 
    for attr in dir(ex):
      b = getattr(ex, attr)
      if isinstance(b, Stateful):
        runhive_classdict[attr] = property(b._hive_stateful_getter, b._hive_stateful_setter)
    classdict = {
      "_hive_runclass": type(cls.__name__+"::runhive", (runhive,), runhive_classdict),
      "_hive_parentclass":cls,
    }
    cls._hive_objectclass = type(cls.__name__+"::hiveobject", (HiveObject,), classdict)
    cls._hive_built = True 
   
  @classmethod
  def extend(hivebase, name, builder, cls=None, hivekwargs=False):
    if cls is not None:
      assert issubclass(cls, object) #cls must be a new-style Python class, e.g. class cls(object): ... 
    builders = hivebase._builders + ((builder, cls),)
    classdict = {
      "_builders":builders,
      "_hive_hivekwargs":hivekwargs,
    }  
    ext = type(name, (hivebase,), classdict)
    return ext

def hive(name, builder, cls=None, hivekwargs=False): #TODO options for namespacing (old frame/hive distinction)
  if cls is not None:
    assert issubclass(cls, object) #cls must be a new-style Python class, e.g. class cls(object): ...
  return Hive.extend(name, builder, cls, hivekwargs)