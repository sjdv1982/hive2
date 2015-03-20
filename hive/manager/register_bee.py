_bees = []

def register_bee(bee):
  assert len(_bees) > 0
  _bees[-1].append(bee)
  
def register_bee_pop():
  assert len(_bees) > 0 #can't pop before push!
  return _bees.pop()
  
def register_bee_push():  
  _bees.append([])