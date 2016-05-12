from collections.abc import Mapping, Sequence


class ListView(Sequence):

    def __init__(self, sequence):
        self._sequence = sequence

    def __getitem__(self, index):
        return self._sequence[index]

    def __len__(self):
        return len(self._sequence)

    def __repr__(self):
        return repr(self._sequence)


class DictView(Mapping):

    def __init__(self, dict_):
        self._dict = dict_

    def __getitem__(self, item):
        return self._dict[item]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def __repr__(self):
        return repr(self._dict)