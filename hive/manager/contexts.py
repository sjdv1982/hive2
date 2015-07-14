from contextlib import contextmanager


_mode = "immediate"
_building_hive = None
_run_hive = None
_bees = []


def get_mode():
    return _mode


def set_mode(mode):
    global _mode
    assert mode in ("immediate", "build"), mode
    _mode = mode


@contextmanager
def hive_mode_as(mode):
    previous_mode = get_mode()
    try:
        set_mode(mode)
        yield

    finally:
        set_mode(previous_mode)


def get_building_hive():
    return _building_hive


def set_building_hive(building_hive):
    global _building_hive
    _building_hive = building_hive


@contextmanager
def building_hive_as(building_hive):
    previous_building_hive = get_building_hive()
    set_building_hive(building_hive)
    yield
    set_building_hive(previous_building_hive)


def get_run_hive():
    return _run_hive


def set_run_hive(run_hive):
    global _run_hive
    _run_hive = run_hive


@contextmanager
def run_hive_as(run_hive):
    previous_run_hive = get_run_hive()
    set_run_hive(run_hive)
    yield
    set_run_hive(previous_run_hive)


def register_bee(bee):
    assert _bees, "No valid state exists registering bees, call register_bee_push()"
    _bees[-1].append(bee)


def register_bee_pop():
    assert _bees, "No valid state exists registering bees"
    return _bees.pop()


def register_bee_push():
    _bees.append([])


@contextmanager
def bee_register_context():
    register_bee_push()
    yield _bees[-1]
    register_bee_pop()
