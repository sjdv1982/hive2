from PyQt5.QtWidgets import QTabWidget, QTabBar
from PyQt5.QtCore import pyqtSignal


class TabViewWidget(QTabWidget):
    on_changed = pyqtSignal(int)
    on_removed = pyqtSignal(int)
    on_inserted = pyqtSignal(int)

    def __init__(self):
        QTabWidget.__init__(self)

        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self.removeTab)
        self.currentChanged.connect(self._tab_changed)

        self.check_tab_closable = None

        self._current_tab_index = None

    def addTab(self, widget, label, closeable=True):
        tab = QTabWidget.addTab(self, widget, label)

        if not closeable:
            self.tabBar().tabButton(tab, QTabBar.RightSide).resize(0, 0)

        return tab

    def removeTab(self, index):
        if callable(self.check_tab_closable):
            if not self.check_tab_closable(index):
                raise PermissionError("Tab close rejected")

        QTabWidget.removeTab(self, index)

    def _tab_changed(self, index):
        previous_index = self._current_tab_index
        self._current_tab_index = index

        self.on_changed.emit(previous_index)

    def tabRemoved(self, index):
        self.on_removed.emit(index)

    def tabInserted(self, index):
        self.on_inserted.emit(index)
