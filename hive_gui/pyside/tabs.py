from PySide.QtGui import *


class TabViewWidget(QTabWidget):

    def __init__(self):
        QTabWidget.__init__(self)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._close_tab)
        self.currentChanged.connect(self._tab_changed)

        self.on_inserted = None
        self.on_removed = None
        self.on_changed = None

        self._closable_tabs = {}
        self._current_tab_index = None

    def addTab(self, widget, label, closeable=True):
        self._closable_tabs[widget] = closeable
        return QTabWidget.addTab(self, widget, label)

    def _close_tab(self, index):
        widget = self.widget(index)
        is_closable = self._closable_tabs[widget]

        if is_closable:
            self.removeTab(index)

    def _tab_changed(self, index):
        previous_index = self._current_tab_index
        self._current_tab_index = index

        if callable(self.on_changed):
            self.on_changed(self, previous_index)

    def tabRemoved(self, index):
        if callable(self.on_removed):
            self.on_removed(self)

    def tabInserted(self, index):
        if callable(self.on_inserted):
            self.on_inserted(self)


