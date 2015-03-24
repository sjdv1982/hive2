_bees = []


def register_bee(bee):
    assert _bees, "No valid state exists registering bees, call register_bee_push()"
    _bees[-1].append(bee)


def register_bee_pop():
    assert _bees, "No valid state exists registering bees"
    return _bees.pop()


def register_bee_push():    
    _bees.append([])