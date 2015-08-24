# Import PySide classes
import sys
import os
import weakref

from PySide.QtCore import *
from PySide.QtGui import *

# Create a Qt application
app = QApplication(sys.argv)

from hive_gui.pyside.view import NodeView
from hive_gui.pyside.node import Node
from hive_gui.pyside.tree import PTree
from hive_gui.pyside.scene import NodeUiScene
from hive_gui.node_manager import NodeManager
from hive_gui.pyside.main_window import MainWindow

from hive_gui.finder import get_hives
import sca as test_sca
import dragonfly

hives = get_hives(test_sca, dragonfly)

window = MainWindow()
window.resize(480, 320)

window.setWindowTitle("Hive Node Editor")

menu_bar = window.menuBar()


def new_tab():
    add_tab("<Untitled>")


def open_file():
    file_name, _ = QFileDialog.getOpenFileName(menu_bar, 'Open hivemap', '/home')
    if not file_name:
        return

    name = os.path.basename(file_name)

    with open(file_name, 'r') as f:
        data = f.read()

        view = add_tab(name)
        view.node_manager.load(data)


def save_as_file():
    file_name, _ = QFileDialog.getSaveFileName(menu_bar, 'Save hivemap', '/home')
    if not file_name:
        return

    index = tab_body.currentIndex()
    view = tab_body.widget(index)

    data = view.node_manager.export()

    with open(file_name, "w") as f:
        f.write(data)

    # Save filename
    view.file_name = file_name

    # Rename tab
    name = os.path.basename(file_name)
    tab_body.setTabText(index, name)

    check_menu_options()


def save_file():
    view = tab_body.currentWidget()
    file_name = view.file_name

    data = view.node_manager.export()

    with open(file_name, "w") as f:
        f.write(data)

    view.filename = file_name


new_action = QAction("&New", menu_bar,
                shortcut=QKeySequence.New,
                statusTip="Create a new file", triggered=new_tab)


load_action = QAction("&Open...", menu_bar,
                shortcut=QKeySequence.Open,
                statusTip="Open an existing file", triggered=open_file)

save_action = QAction("&Save", menu_bar,
                shortcut=QKeySequence.Save,
                statusTip="Save as existing new file", triggered=save_file)

save_as_action = QAction("&Save As...", menu_bar,
                shortcut=QKeySequence.SaveAs,
                statusTip="Save as a new file", triggered=save_as_file)

file_menu = menu_bar.addMenu("&File")

file_menu.addAction(new_action)
file_menu.addAction(load_action)
file_menu.addAction(save_action)
file_menu.addAction(save_as_action)

save_as_action.setVisible(False)

window.show()


class NodeEditor(QWidget):

    def __init__(self):

# Left window
selector_window = window.create_subwindow("Hives", "left")
hive_tree = PTree()
selector_window.setWidget(hive_tree._widget)
hive_tree.load_hives(hives)


def add_worker(path):
    view = tab_body.currentWidget()
    view.pending_create_path = path


hive_tree.on_selected = add_worker


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

    def addTab(self, widget, label, closeable=True):
        self._closable_tabs[widget] = closeable
        QTabWidget.addTab(self, widget, label)

    def _close_tab(self, index):
        widget = self.widget(index)
        is_closable = self._closable_tabs[widget]

        if is_closable:
            self.removeTab(index)

    def _tab_changed(self, index):
        if callable(self.on_changed):
            self.on_changed(self)

    def tabRemoved(self, index):
        if callable(self.on_removed):
            self.on_removed(self)

    def tabInserted(self, index):
        if callable(self.on_inserted):
            self.on_inserted(self)


tab_body = TabViewWidget()
window.setCentralWidget(tab_body)

def check_menu_options():
    widget = tab_body.currentWidget()

    show_save = False
    show_save_as = False

    if isinstance(widget, NodeView):
        show_save_as = True
        show_save = widget.file_name is not None

    save_action.setVisible(show_save)
    save_as_action.setVisible(show_save_as)

# on changed callback
def on_tab_changed(tab_menu):
    check_menu_options()

tab_body.on_changed = on_tab_changed

# Add Help page
from PySide.QtWebKit import *
import hive_gui.pyside as py_gui

help_widget = QWebView()
tab_body.addTab(help_widget, "Home", closeable=False)

# Load Help data
html_file_name = os.path.join(py_gui.__path__[0], "home.html")
with open(html_file_name) as f:
    help_widget.setHtml(f.read())


def add_tab(name):
    view = NodeView()
    tab_body.addTab(view, name)

    node_manager = NodeManager(view)
    view.node_manager = node_manager

    scene = NodeUiScene()
    view.setScene(scene)

    view.show()

    return view

#TODO make windowing more dynamic
#TODO support configuration of hives before adding
#TODO support io pins


# Enter Qt application main loop
app.exec_()
sys.exit()