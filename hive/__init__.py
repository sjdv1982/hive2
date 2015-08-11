from .manager import get_building_hive, get_mode, get_run_hive
from .hive import hive, HiveBuilder, RuntimeHive, HiveObject

#i primitives
from .triggerfunc import triggerfunc
from .triggerable import triggerable
from .modifier import modifier #(akin to triggerable, but receives run_hive as self)
from .ppin import push_in, pull_in
from .ppout import push_out, pull_out
from .variable import variable

#connection primitives
from .connect import connect
from .trigger import trigger

#i/ex primitives
from .property import property
from .attribute import attribute

#ex primitives
from .entry import entry
from .hook import hook
from .socket import socket
from . import socket_policies
from .plugin import plugin
from . import plugin_policies
from .antenna import antenna
from .output import output

#args primitives
from .parameter import parameter

# TODO: NO autosocket! instead, add a name argument to sockets and plugins, and an optional "autosocket" argument to HiveObject.__init__
# TODO: autosocket default policy (for parent and for children) on args object
#    - if there are named sockets, a policy towards the parent MUST be defined
#    - a policy towards the children is optional     