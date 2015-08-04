try:
    advance_iterator = next

except NameError:
    def advance_iterator(it):
        return it.next()

next = advance_iterator