from __future__ import print_function, absolute_import

from PyQt5.QtCore import pyqtSignal, QEvent
from PyQt5.QtWidgets import QTreeWidget, QAbstractItemView, QTreeWidgetItem


class TreeWidget(QTreeWidget):
    onSelected = pyqtSignal(str)
    onDoubleClick = pyqtSignal(str)
    onRightClick = pyqtSignal(str, QEvent)

    def __init__(self, parent=None):
        super(TreeWidget, self).__init__(parent)

        self.setColumnCount(1)
        self.setHeaderHidden(True)

        self._keys = []
        self._allItems = {}
        self._widgetIdToKey = {}
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemPressed.connect(self._onItemClicked)
        self.itemDoubleClicked.connect(self._onItemDoubleClicked)
        self.setDragEnabled(True)

    def clear(self):
        self._keys.clear()
        self._allItems.clear()
        self._widgetIdToKey.clear()

        super(TreeWidget, self).clear()

    def contextMenuEvent(self, event):
        item = self.selectedItems()[0]

        try:
            key = self._widgetIdToKey[id(item)]

        except KeyError:
            return

        path = '.'.join(key)
        self.onRightClick.emit(path, event)

    def _onItemClicked(self, item, column):
        if id(item) in self._widgetIdToKey:
            key = self._widgetIdToKey[id(item)]

            path = '.'.join(key)
            self.onSelected.emit(path)

            self.setDragEnabled(True)
        else:
            self.setDragEnabled(False)

    def _onItemDoubleClicked(self, item, column):
        if id(item) in self._widgetIdToKey:
            key = self._widgetIdToKey[id(item)]

            path = '.'.join(key)
            self.onDoubleClick.emit(path)

            self.setDragEnabled(True)
        else:
            self.setDragEnabled(False)

    def setItems(self, items):
        self.clear()

        for item in items:
            self.append(item)

    def append(self, path):
        assert isinstance(path, str)

        key = path.split('.')
        assert key not in self._keys
        head, tail = key[0], key[1:]

        if head not in self._allItems:
            item = QTreeWidgetItem()
            item.setText(0, head)
            self._allItems[head] = item

            self.addTopLevelItem(item)
            widget = item

        else:
            widget = self._allItems[head]

        prev = (head,)

        while tail:
            head, tail = tail[0], tail[1:]
            phead = prev + (head,)

            if phead not in self._allItems:
                item = QTreeWidgetItem()
                item.setText(0, head)
                widget.addChild(item)
                self._allItems[phead] = item
                widget = item

            else:
                widget = self._allItems[phead]

            prev = phead

        key = tuple(key)

        self._keys.append(key)
        self._widgetIdToKey[id(widget)] = key

    def _removeEmptyGroup(self, group):
        g = len(group)
        nr_items = len([k for k in self._allItems.keys() if k[:g] == group])
        min = 1 if g > 1 else 0
        if nr_items == min:
            if len(group) == 1:
                group = group[0]
                w = self._allItems.pop(group)
                ind = self.indexOfTopLevelItem(w)
                self.takeTopLevelItem(ind)
            else:
                w = self._allItems.pop(group)
                parent = group[:-1]
                if len(parent) == 1: parent = parent[0]
                ww = self._allItems[parent]
                ww.removeChild(w)

    def remove(self, path):
        assert isinstance(path, str)
        key = path.split('.')
        assert key in self._keys

        self._keys.remove(key)
        item = self._allItems.pop(key)
        self._widgetIdToKey.pop(id(item))

        if len(key) == 1:
            ind = self.indexOfTopLevelItem(item)
            self.takeTopLevelItem(ind)

        else:
            parent = key[:-1]
            if len(parent) == 1:
                parent = parent[0]

            ww = self._allItems[parent]
            ww.removeChild(item)

        for n in range(len(key), 0, -1):
            group = key[:n]
            self._removeEmptyGroup(group)
