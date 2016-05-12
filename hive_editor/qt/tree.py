from __future__ import print_function, absolute_import

from PyQt5.QtCore import pyqtSignal, QEvent
from PyQt5.QtWidgets import QTreeWidget, QAbstractItemView, QTreeWidgetItem


class TreeWidget(QTreeWidget):
    on_selected = pyqtSignal(str)
    on_right_click = pyqtSignal(str, QEvent)

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.setColumnCount(1)
        self.setHeaderHidden(True)

        self._keys = []
        self.all_items = {}
        self._widget_id_to_key = {}
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemPressed.connect(self._on_item_pressed)
        self.setDragEnabled(True)

    def contextMenuEvent(self, event):
        item = self.selectedItems()[0]

        try:
            key = self._widget_id_to_key[id(item)]

        except KeyError:
            return

        path = '.'.join(key)
        self.on_right_click.emit(path, event)

    def _on_item_pressed(self, item, column):
        if id(item) in self._widget_id_to_key:
            key = self._widget_id_to_key[id(item)]

            path = '.'.join(key)
            self.on_selected.emit(path)

            self.setDragEnabled(True)
        else:
            self.setDragEnabled(False)

    def load_items(self, item_dict, path=()):
        for name, child in item_dict.items():
            full_path = path + (name,)

            if isinstance(child, dict):
                self.load_items(child, full_path)

            else:
                assert child is None
                self.append(full_path)

    def append(self, key):
        assert key not in self._keys
        head, tail = key[0], key[1:]

        if head not in self.all_items:
            item = QTreeWidgetItem()
            item.setText(0, head)
            self.all_items[head] = item

            self.addTopLevelItem(item)
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
        self._widget_id_to_key[id(widget)] = key

    def _remove_empty_group(self, group):
        g = len(group)
        nr_items = len([k for k in self.all_items.keys() if k[:g] == group])
        min = 1 if g > 1 else 0
        if nr_items == min:
            if len(group) == 1:
                group = group[0]
                w = self.all_items.pop(group)
                ind = self.indexOfTopLevelItem(w)
                self.takeTopLevelItem(ind)
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
        item = self.all_items.pop(key)
        self._widget_id_to_key.pop(id(item))

        if len(key) == 1:
            ind = self.indexOfTopLevelItem(item)
            self.takeTopLevelItem(ind)

        else:
            parent = key[:-1]
            if len(parent) == 1:
                parent = parent[0]

            ww = self.all_items[parent]
            ww.removeChild(item)

        for n in range(len(key), 0, -1):
            group = key[:n]
            self._remove_empty_group(group)
