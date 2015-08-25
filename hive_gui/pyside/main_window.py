from PySide.QtCore import *
from PySide.QtGui import *

import os

from .tabs import TabViewWidget
from .view import NodeView
from .tree import PTree
from .scene import NodeUiScene

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

        file_menu = menu_bar.addMenu("&File")

        file_menu.addAction(self.new_action)
        file_menu.addAction(self.load_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)

        self.save_as_action.setVisible(False)

        # Add tab widget
        self.tab_widget = TabViewWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab_widget.on_changed = self.on_tab_changed

        # Left window
        self.selector_window = self.create_subwindow("Hives", "left")
        self.hive_tree = PTree()
        self.hive_tree.on_selected = self.inform_view_of_dropped_worker
        self.selector_window.setWidget(self.hive_tree.widget())

        # Docstring editor
        self.docstring_window = self.create_subwindow("Docstring", "left")
        self.docstring_window.setVisible(False)

        # Add text area
        self.docstring_editor = QTextEdit()
        self.docstring_window.setWidget(self.docstring_editor)

        self.home_page = None

    def load_home_page(self, home_page):
        self.tab_widget.addTab(home_page, "Home", closeable=False)
        self.home_page = home_page

    def on_tab_changed(self, tab_menu):
        # Update UI elements
        self.update_ui_layout()

        widget = tab_menu.currentWidget()

        # Replace docstring
        if isinstance(widget, NodeView):
            self.docstring_editor.setPlainText(widget.node_manager.docstring)

    def add_node_view(self, name="<Untitled>"):
        view = NodeView()

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

        if isinstance(widget, NodeView):
            show_save_as = True
            show_save = widget.file_name is not None
            show_docstring = True

        self.save_action.setVisible(show_save)
        self.save_as_action.setVisible(show_save_as)
        self.docstring_window.setVisible(show_docstring)

    def inform_view_of_dropped_worker(self, path):
        view = self.tab_widget.currentWidget()
        view.pending_create_path = path

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self.menuBar(), 'Open hivemap', '/home')
        if not file_name:
            return

        view = self.add_node_view()
        view.load(file_name=file_name)

        # Load docstring
        self.docstring_editor.setPlainText(view.docstring)

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

        view.docstring = self.docstring_editor.toPlainText()

        # Before we attempt to save
        was_untitled = view.is_untitled

        view.save(file_name=file_name)

        # Newly saved
        if was_untitled:
            # Rename tab
            name = os.path.basename(file_name)
            index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(index, name)

            # Update save UI elements now we have a filename
            self.update_ui_layout()