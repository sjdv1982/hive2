from PySide.QtCore import *
from PySide.QtGui import *

import os

from .tabs import TabViewWidget
from .view import NodeView
from .tree import PTree
from .scene import NodeUiScene
from .configuration import NodeConfigurationPanel
from ..node_manager import NodeManager

area_classes = {
    "left": Qt.LeftDockWidgetArea,
    "right": Qt.RightDockWidgetArea,
    "top": Qt.TopDockWidgetArea,
    "bottom": Qt.BottomDockWidgetArea,
}


class MainWindow(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self.setWindowTitle("Hive Node Editor")

        menu_bar = self.menuBar()

        self.new_action = QAction("&New", menu_bar,
                        shortcut=QKeySequence.New,
                        statusTip="Create a new file", triggered=self.add_node_view)

        self.load_action = QAction("&Open...", menu_bar,
                        shortcut=QKeySequence.Open,
                        statusTip="Open an existing file", triggered=self.open_file)

        self.save_action = QAction("&Save", menu_bar,
                        shortcut=QKeySequence.Save,
                        statusTip="Save as existing new file", triggered=self.save_file)

        self.save_as_action = QAction("&Save As...", menu_bar,
                        shortcut=QKeySequence.SaveAs,
                        statusTip="Save as a new file", triggered=self.save_as_file)

        self.file_menu = QMenu("&File")

        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.load_action)
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)

        self.select_all_action = QAction("Select &All", menu_bar,
                                   shortcut=QKeySequence.SelectAll,
                                   statusTip="Select all nodes", triggered=self.select_all_operation)

        self.undo_action = QAction("&Undo", menu_bar,
                                   shortcut=QKeySequence.Undo,
                                   statusTip="Undo last operation", triggered=self.undo_operation)

        self.redo_action = QAction("&Redo", menu_bar,
                                   shortcut=QKeySequence.Redo,
                                   statusTip="Redo last operation", triggered=self.redo_operation)

        self.copy_action = QAction("&Copy", menu_bar,
                                   shortcut=QKeySequence.Copy,
                                   statusTip="Copy selected nodes", triggered=self.copy_operation)

        self.cut_action = QAction("Cu&t", menu_bar,
                                   shortcut=QKeySequence.Cut,
                                   statusTip="Cut selected nodes", triggered=self.cut_operation)

        self.paste_action = QAction("&Paste", menu_bar,
                                   shortcut=QKeySequence.Paste,
                                   statusTip="Paste selected nodes", triggered=self.paste_operation)

        self.edit_menu = QMenu("&Edit")

        self.edit_menu.addAction(self.select_all_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.cut_action)
        self.edit_menu.addAction(self.copy_action)
        self.edit_menu.addAction(self.paste_action)

        self.save_as_action.setVisible(False)

        # Add tab widget
        self.tab_widget = TabViewWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab_widget.on_changed = self.on_tab_changed

        # Left window
        self.selector_window = self.create_subwindow("Hives", "left")
        self.hive_tree = PTree()
        self.hive_tree.on_selected = self.on_dropped_hive_node
        self.selector_window.setWidget(self.hive_tree.widget())

        # Docstring editor
        self.docstring_window = self.create_subwindow("Docstring", "left")
        self.docstring_window.setVisible(False)

        self.configuration_window = self.create_subwindow("Configuration", "right")
        self.docstring_window.setVisible(False)

        self.home_page = None

    def get_current_node_manager(self):
        view = self.tab_widget.currentWidget()
        return view.node_manager

    def select_all_operation(self):
        view = self.tab_widget.currentWidget()
        view.select_all()

    def undo_operation(self):
        view = self.tab_widget.currentWidget()
        view.undo()

    def redo_operation(self):
        view = self.tab_widget.currentWidget()
        view.redo()

    def copy_operation(self):
        view = self.tab_widget.currentWidget()
        view.copy()

    def cut_operation(self):
        view = self.tab_widget.currentWidget()
        view.cut()

    def paste_operation(self):
        view = self.tab_widget.currentWidget()
        view.paste()

    def load_home_page(self, home_page):
        self.tab_widget.addTab(home_page, "Home", closeable=False)
        self.home_page = home_page

    def on_tab_changed(self, tab_menu, previous_index=None):
        # Exit last open view
        if previous_index is not None:
            previous_widget = tab_menu.widget(previous_index)
            if isinstance(previous_widget, NodeView):
                previous_widget.on_exit()

        # Update UI elements
        self.update_ui_layout()

        widget = tab_menu.currentWidget()

        # Replace docstring
        if isinstance(widget, NodeView):
            widget.on_enter()

    def add_node_view(self, name="<Untitled>"):
        view = NodeView(self.configuration_window, self.docstring_window)

        index = self.tab_widget.addTab(view, name)
        self.tab_widget.setCurrentIndex(index)

        scene = NodeUiScene()
        view.setScene(scene)

        view.show()

        return view

    def create_subwindow(self, title, position):
        area = area_classes[position]
        window = QDockWidget(title, self)
        child = QWidget()
        window.setWidget(child)
        self.addDockWidget(area, window)
        return window

    def update_ui_layout(self):
        widget = self.tab_widget.currentWidget()

        show_save = False
        show_save_as = False
        show_docstring = False
        show_edit = False

        if isinstance(widget, NodeView):
            show_save_as = True
            show_save = widget.file_name is not None
            show_docstring = True
            show_edit = True

        self.save_action.setVisible(show_save)
        self.save_as_action.setVisible(show_save_as)
        self.docstring_window.setVisible(show_docstring)

        menu_bar = self.menuBar()
        menu_bar.clear()

        menu_bar.addMenu(self.file_menu)

        if show_edit:
            menu_bar.addMenu(self.edit_menu)

    def on_dropped_hive_node(self, path):
        view = self.tab_widget.currentWidget()
        view.pre_drop_hive(path)

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self.menuBar(), 'Open hivemap', '/home')
        if not file_name:
            return

        view = self.add_node_view()
        view.load(file_name=file_name)

        # Rename tab
        name = os.path.basename(file_name)
        index = self.tab_widget.currentIndex()
        self.tab_widget.setTabText(index, name)

        # Update save UI elements now we have a filename
        self.update_ui_layout()

    def save_as_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self.menuBar(), 'Save hivemap', '/home')
        if not file_name:
            return

        # Perform save
        self.save_file(file_name)

    def save_file(self, file_name=None):
        view = self.tab_widget.currentWidget()
        assert isinstance(view, NodeView)

        view.save(file_name=file_name)

        # Newly saved
        if file_name is not None:
            # Rename tab
            name = os.path.basename(file_name)
            index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(index, name)

            # Update save UI elements now we have a filename
            self.update_ui_layout()