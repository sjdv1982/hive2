Control flow: Generic node manager -> Blender node manager

# Debugger
- [ ] Step by step display of node sockets involved in operation
- [ ] Preview data (maybe show when types mismatch) - debug stack in corner
- [ ] Use config options - write to file, socket (port etc)

# Blender GUI
- [x] Don't bother inspecting UI on loading, just wipe and re-load
- [x] When adding nodes, operator will setup data first then add GUI representation
- [x] When copying nodes, GUI will notice was copied and configure #{Instead, we trash and reload}
- [ ] When trying something that fails, undo (e.g create_con)
- [ ] How to fix edit undo?
- [ ] Draw docstring inside nodes using draw_buttons - use RuntimeNode.__doc__? - pass to hive.extend, expose using __doc__ or .help() or .info()

# QTGUI
- [x] Make connections deletable
- [x] Add copy / paste
- [x] Check out pos/ scene pos discrepancy
- [x] Add edit undo
- [x] Add select tools, grab etc

# General GUI
- [x] Add docstring to builder function when building from hivemap
- [ ] Import hivemaps as nodes into other hivemaps - design _hive project?_
- [x] Foldable variables (pull in)
    * If > 1 connection, can't fold
    * Support hide/show - Infer if connected node is hidden, is folded. (If hide node, notify connections!)
    * Only cut visible connections
    * Allow view to populate this in main window? view->set_node_config->... (set options OR set actual form layout) -> More powerful system for config and other things?? window node "context"
- [ ] Support modifier bees?

* Node Finder
    - [x] Parse all hives (just check if inherits from HiveBuilder)
    - [ ] Parse all bees (just check if inherits from Bee)

* How to support meta-hives / declarators in GUI?
* Use bees (hive.antenna, entry, hook, output) to define hive IO interface
    Should this be a subset of the bees, handled manually?

    ##Support bees with hives:
    1. Restructure hive / bee distinction?
    2. Use optional from_socket to_socket in model.BeeConnection?
    3. Account for fact that bee != hivebee, maybe add another layer / more generic setup?

* Add ability to inspect built-in node. If nested hives, recurse to greater and greater depths - open their hivemaps,
                                or generate hivemap, but don't guarantee utility (maybe read only?)

* Should all hivemap bees be internal where possible?

* Support user defined hives as bees in editor:
  * If updated show warning - need to update
  * If operator pressed, find connected nodes, remember and disconnect them.
  * Recreate node & attempt to recreate connections

- [ ] Show/hide sockets and plugins?
- [x] Unfold / fold input pull attributes?
- [x] Metahives - avoid rebuilding entire hive!

# Axioms
  * Node pins aren't renameable