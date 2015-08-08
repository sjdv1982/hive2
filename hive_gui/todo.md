Control flow: Generic node manager -> Blender node manager

# Blender GUI
- [x] Don't bother inspecting UI on loading, just wipe and re-load
- [x] When adding nodes, operator will setup data first then add GUI representation
- [x] When copying nodes, GUI will notice was copied and configure #{Instead, we trash and reload}
- [ ] How to fix edit undo?
- [ ] Draw docstring inside nodes using draw_buttons - use RuntimeNode.__doc__? - pass to hive.extend, expose using __doc__ or .help() or .info()

# General GUI
* Node Finder
    * Parse all hives (just check if inherits from HiveBuilder)
    * Parse all bees (just check if inherits from Bee)
    * Parse all parameters (just check if inherits from Parameter)

* How to support meta-hives / declarators in GUI?
* Use bees (hive.antenna, entry, hook, output) to define hive IO interface
    Should this be a subset of the bees, handled manually?

    ##Support bees with hives:
    1. Restructure hive / bee distinction?
    2. Use optional from_socket to_socket in model.BeeConnection?
    3. Account for fact that bee != hivebee, maybe add another layer / more generic setup?

* Add ability to inspect built-in node. If nested hives, recurse to greater and greater depths - open their hivemaps,
                                or generate hivemap, but don't guarantee utility (maybe read only?)

* Should all hivemap bees bee internal where possible?

* Support user defined hives as bees in editor:
  * If updated show warning - need to update
  * If operator pressed, find connected nodes, remember and disconnect them.
  * Recreate node & attempt to recreate connections
