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

        self._current_tab_index = None

    def addTab(self, widget, label, closeable=True):
        tab = QTabWidget.addTab(self, widget, label)

        if not closeable:
            self.tabBar().tabButton(tab, QTabBar.RightSide).resize(0, 0)

        return tab

    def _close_tab(self, index):
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


