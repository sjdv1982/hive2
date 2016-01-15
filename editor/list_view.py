class ListView:

    def __init__(self, sequence):
        self._sequence = sequence

    def index(self, item):
        return self._sequence.index(item)

    def __getitem__(self, index):
        return self._sequence[index]

    def __bool__(self):
        return bool(self._sequence)

    def __contains__(self, item):
        return item in self._sequence

    def __len__(self):
        return len(self._sequence)

    def __iter__(self):
        return iter(self._sequence)

    def __repr__(self):
        return repr(self._sequence)
