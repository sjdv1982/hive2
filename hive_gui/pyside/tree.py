from __future__ import print_function, absolute_import

from PySide import QtGui, QtCore
from PySide.QtGui import QTreeWidgetItem


class PTree(object):

    def __init__(self, parent=None, on_selected=None):
        self._widget = QtGui.QTreeWidget(parent)
        self._widget.setColumnCount(1)
        self._keys = []
        self.all_items = {}
        self._leafitems_rev = {}
        self._widget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self._widget.itemPressed.connect(self._itemPressed)
        self._widget.setDragEnabled(True)
        self.on_selected = on_selected

    def widget(self):
        return self._widget

    def _itemPressed(self, item, column):
        if id(item) in self._leafitems_rev:
            key = self._leafitems_rev[id(item)]

            if callable(self.on_selected):
                path = '.'.join(key)
                self.on_selected(path)

            self._widget.setDragEnabled(True)
        else:
            self._widget.setDragEnabled(False)

    def load_hives(self, hives, path=()):
        for name, children in hives.items():

            full_path = path + (name,)

            for child in children:
                if isinstance(child, dict):
                    self.load_hives(child, full_path)

                else:
                    self.append(full_path + (child,))

    def append(self, key):
        assert key not in self._keys
        head, tail = key[0], key[1:]

        if head not in self.all_items:
            item = QTreeWidgetItem()
            item.setText(0, head)
            self.all_items[head] = item

            self._widget.addTopLevelItem(item)
            widget = item

        else:
            widget = self.all_items[head]

        prev = (head,)

        while tail:
            head, tail = tail[0], tail[1:]
            phead = prev + (head,)

            if phead not in self.all_items:
                item = QTreeWidgetItem()
                item.setText(0, head)
                widget.addChild(item)
                self.all_items[phead] = item
                widget = item

            else:
                widget = self.all_items[phead]

            prev = phead

        key = tuple(key)
        self._keys.append(key)
        self._leafitems_rev[id(widget)] = key

    def _remove_empty_group(self, group):
        g = len(group)
        nr_items = len([k for k in self.all_items.keys() if k[:g] == group])
        min = 1 if g > 1 else 0
        if nr_items == min:
            if len(group) == 1:
                group = group[0]
                w = self.all_items.pop(group)
                ind = self._widget.indexOfTopLevelItem(w)
                self._widget.takeTopLevelItem(ind)
            else:
                w = self.all_items.pop(group)
                parent = group[:-1]
                if len(parent) == 1: parent = parent[0]
                ww = self.all_items[parent]
                ww.removeChild(w)

    def remove(self, key):
        key = tuple(key)
        assert key in self._keys

        self._keys.remove(key)
        w = self.all_items.pop(key)
        self._leafitems_rev.pop(id(w))
        if len(key) == 1:
            ind = self._widget.indexOfTopLevelItem(w)
            self._widget.takeTopLevelItem(ind)

        else:
            parent = key[:-1]
            if len(parent) == 1:
                parent = parent[0]

            ww = self.all_items[parent]
            ww.removeChild(w)

        for n in range(len(key), 0, -1):
            group = key[:n]
            self._remove_empty_group(group)

    def sync(self):
        pass
