from .qt_gui import *


class TabViewWidget(QTabWidget):

    def __init__(self):
        QTabWidget.__init__(self)

        self.setTabsClosable(True)
        self.setAcceptDrops(True)

        self.tabCloseRequested.connect(self.removeTab)
        self.currentChanged.connect(self._tab_changed)

        self.on_inserted = None
        self.on_removed = None
        self.on_changed = None
        self.check_valid_drop = None
        self.on_dropped = None
        self.check_tab_closable = None

        self._current_tab_index = None

    def dragEnterEvent(self, event):
        if callable(self.check_valid_drop):
            if self.check_valid_drop(event):
                event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if callable(self.on_dropped):
            self.on_dropped(event)

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

        if callable(self.on_changed):
            self.on_changed(self, previous_index)

    def tabRemoved(self, index):
        if callable(self.on_removed):
            self.on_removed(self)

    def tabInserted(self, index):
        if callable(self.on_inserted):
            self.on_inserted(self)


