from PyQt5.QtWidgets import QTabWidget, QTabBar
from PyQt5.QtCore import pyqtSignal


class TabViewWidget(QTabWidget):
    onTabChanged = pyqtSignal(int)
    onTabRemoved = pyqtSignal(int)
    onTabInserted = pyqtSignal(int)

    def __init__(self):
        QTabWidget.__init__(self)

        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self.removeTab)
        self.currentChanged.connect(self._onTabChanged)

        self.checkTabClosable = None

        self._currentTabIndex = None

    def addTab(self, widget, label, closeable=True):
        tab = QTabWidget.addTab(self, widget, label)

        if not closeable:
            self.tabBar().tabButton(tab, QTabBar.RightSide).resize(0, 0)

        return tab

    def removeTab(self, index):
        if callable(self.checkTabClosable):
            if not self.checkTabClosable(index):
                raise PermissionError("Tab close rejected")

        QTabWidget.removeTab(self, index)

    def _onTabChanged(self, index):
        previous_index = self._currentTabIndex
        self._currentTabIndex = index

        self.onTabChanged.emit(previous_index)

    def tabRemoved(self, index):
        self.onTabRemoved.emit(index)

    def tabInserted(self, index):
        self.onTabInserted.emit(index)
