from . import manager

_mode = "immediate"
_building_hive = None
_run_hive = None


def get_mode():
    return _mode


def set_mode(mode):
    global _mode
    assert mode in ("immediate", "build"), mode
    _mode = mode


def get_building_hive():
    return _building_hive


def set_building_hive(building_hive):
    global _building_hive    
    assert building_hive is None or issubclass(building_hive, HiveBuilder), building_hive
    _building_hive = building_hive


def get_run_hive():
    return _run_hive


def set_run_hive(run_hive):
    global _run_hive
    assert run_hive is None or isinstance(run_hive, RuntimeHive), run_hive
    _run_hive = run_hive


from .hive import hive, HiveBuilder, RuntimeHive

#i primitives
from .triggerfunc import triggerfunc
from .triggerable import triggerable
from .modifier import modifier #(akin to triggerable, but receives run_hive as self)
from .ppin import pushin, pullin
from .ppout import pushout, pullout

#connection primitives
from .connect import connect
from .trigger import trigger

#i/ex primitives
from .property import property
from .attribute import attribute #(akin to property, but is stored on the run_hive)

#ex primitives
from .entry import entry
from .hook import hook
from .socket import socket
from .plugin import plugin
from .antenna import antenna
from .output import output
# TODO: NO autosocket! instead, add a name argument to sockets and plugins, and an optional "autosocket" argument to HiveObject.__init__
# TODO: supplier, required etc. for sockets/plugins
# TODO: autosocket default policy (for parent and for children) on args object
#    - if there are named sockets, a policy towards the parent MUST be defined
#    - a policy towards the children is optional     