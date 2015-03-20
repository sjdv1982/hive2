"""
Stateful mixin
Hives that are Stateful behave differently when added to the i wrapper
Instead of adding the whole hive instance, a *Python attribute* is added to the wrapper
The getter/setter of this attribute are hiveinstance._hive_stateful.getter and hiveinstance._hive_stateful.setter, 
 respectively
 
A Stateful object's getter/setter always accept a runhive object, which will be None in immediate mode 
"""

class Stateful(object):
  def _hive_stateful_getter(self, runhive):
    raise NotImplementedError
  def _hive_stateful_setter(self, runhive, value):
    raise NotImplementedError  