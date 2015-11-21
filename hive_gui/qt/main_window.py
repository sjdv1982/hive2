import os
import webbrowser

from functools import partial

from .qt_core import *
from .qt_gui import *
from .tabs import TabViewWidget
from .tree import TreeWidget
from .node_editor import NodeEditorSpace

from ..finder import found_bees, HiveFinder
from ..importer import clear_imported_hivemaps
from ..node import NodeTypes
from ..utils import import_path_to_module_file_path

area_classes = {
    "left": Qt.LeftDockWidgetArea,
    "right": Qt.RightDockWidgetArea,
    "top": Qt.TopDockWidgetArea,
    "bottom": Qt.BottomDockWidgetArea,
}

# TODO throw unsaved warning when closing tabs


class MainWindow(QMainWindow):
    project_name_template = "Hive Node Editor - {}"

    def __init__(self):
        QMainWindow.__init__(self)

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self.setWindowTitle(self.project_name_template.format("<No Project>"))

        menu_bar = self.menuBar()

        self.new_action = QAction("&New", menu_bar,
                        shortcut=QKeySequence.New,
                        statusTip="Create a new file", triggered=self.add_editor_space)

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

        self.open_project_action = QAction("Open Project", menu_bar,
                                   statusTip="Open an existing Hive project", triggered=self.open_project)

        self.close_project_action = QAction("Close Project", menu_bar,
                                   statusTip="Close the current Hive project", triggered=self.close_project)

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

        self.help_action = QAction("&Help", menu_bar, statusTip="Open Help page in browser", triggered=self.goto_help_page)

        self.save_as_action.setVisible(False)

        # Add tab widget
        self.tab_widget = TabViewWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab_widget.on_changed = self.on_tab_changed

        # Left window
        self.bee_window = self.create_subwindow("Bees", "left")

        # Left window
        self.hive_window = self.create_subwindow("Hives", "left")
        self.hive_window.setMinimumHeight(450)

        # Docstring editor
        self.docstring_window = self.create_subwindow("Docstring", "left")
        self.configuration_window = self.create_subwindow("Configuration", "right")
        self.parameter_window = self.create_subwindow("Parameters", "right")
        self.folding_window = self.create_subwindow("Folding", "right")
        self.preview_window = self.create_subwindow("Preview", "left")

        self.tabifyDockWidget(self.hive_window, self.bee_window)

        self.home_page = None

        self.project_directory = None
        self.hive_finder = HiveFinder()

    def goto_help_page(self):
        webbrowser.open("https://github.com/agoose77/hive2/wiki")

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
        self.tab_widget.addTab(home_page, "About", closeable=False)
        self.home_page = home_page

    def on_tab_changed(self, tab_menu, previous_index=None):
        # Exit last open view
        if previous_index is not None:
            previous_widget = tab_menu.widget(previous_index)

            if isinstance(previous_widget, NodeEditorSpace):
                previous_widget.on_exit(self.docstring_window, self.folding_window, self.configuration_window,
                                        self.parameter_window, self.preview_window)

        # Update UI elements
        self.update_ui_layout()

        widget = tab_menu.currentWidget()

        # Replace docstring
        if isinstance(widget, NodeEditorSpace):
            widget.on_enter(self.docstring_window, self.folding_window, self.configuration_window,
                            self.parameter_window, self.preview_window)

    def add_editor_space(self, *, file_name=None):
        editor = NodeEditorSpace(file_name)

        if file_name is None:
            label = "<Unsaved>"
        else:
            label = file_name

        index = self.tab_widget.addTab(editor, label)
        self.tab_widget.setCurrentIndex(index)

        editor.show()

        return editor

    def create_subwindow(self, title, position, closeable=False):
        area = area_classes[position]

        window = QDockWidget(title, self)
        features = QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable
        if closeable:
            features |= QDockWidget.DockWidgetClosable

        window.setFeatures(features)

        child = QWidget()
        window.setWidget(child)
        self.addDockWidget(area, window)
        return window

    def update_ui_layout(self):
        show_save = False
        show_save_as = False

        show_edit = False

        show_docstring = True
        show_config = True
        show_folding = True
        show_hives = True
        show_args = True
        show_bees = True
        show_preview = True

        menu_bar = self.menuBar()
        menu_bar.clear()

        menu_bar.addMenu(self.file_menu)
        self.file_menu.clear()

        self.file_menu.addAction(self.open_project_action)

        if self.project_directory is not None:
            print("SHOE")
            self.file_menu.addAction(self.close_project_action)

        widget = self.tab_widget.currentWidget()

        if isinstance(widget, NodeEditorSpace):
            show_save_as = True
            show_save = widget.file_name is not None
            show_edit = True

        self.save_action.setVisible(show_save)
        self.save_as_action.setVisible(show_save_as)

        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.load_action)

        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)

        if show_edit:
            menu_bar.addMenu(self.edit_menu)

        menu_bar.addAction(self.help_action)

        # Static visibilities
        self.docstring_window.setVisible(show_docstring)
        self.folding_window.setVisible(show_folding)
        self.configuration_window.setVisible(show_config)
        self.hive_window.setVisible(show_hives)
        self.bee_window.setVisible(show_bees)
        self.parameter_window.setVisible(show_args)
        self.preview_window.setVisible(show_preview)

    def on_dropped_hive_node(self, path):
        view = self.tab_widget.currentWidget()

        if isinstance(view, NodeEditorSpace):
            view.pre_drop_hive(path)

    def on_selected_tree_node(self, path, node_type):
        widget = self.tab_widget.currentWidget()

        if not isinstance(widget, NodeEditorSpace):
            return

        widget.pre_drop_node(path, node_type)

    def open_project(self):
        dialogue = QFileDialog(self, caption="Open Hive Project")
        dialogue.setFileMode(QFileDialog.DirectoryOnly)
        dialogue.setAcceptMode(QFileDialog.AcceptOpen)
        dialogue.setOption(QFileDialog.ShowDirsOnly)

        if not dialogue.exec_():
            return

        directory_path = dialogue.selectedFiles()[0]

        self._close_project()

        self.project_directory = directory_path
        self.hive_finder.additional_paths = {directory_path, }

        # Rename application title
        project_name = os.path.basename(directory_path)
        self.setWindowTitle(self.project_name_template.format(project_name))

        self.refresh_project_tree()

        self.update_ui_layout()

    def close_project(self):
        self._close_project()

        self.update_ui_layout()

    def _close_project(self):
        # Close open tabs
        while self.tab_widget.count() > 1:
            self.tab_widget.removeTab(1)

        clear_imported_hivemaps()

        self.hive_finder.additional_paths.clear()
        self.refresh_project_tree()

        self.project_directory = None

    def refresh_project_tree(self):
        self.hive_widget = TreeWidget()
        self.hive_widget.on_selected = partial(self.on_selected_tree_node, node_type=NodeTypes.HIVE)
        self.hive_window.setWidget(self.hive_widget)
        self.hive_widget.load_items(self.hive_finder.find_hives())
        self.hive_widget.on_right_click = self.show_hive_edit_menu

        self.bee_widget = TreeWidget()
        self.bee_widget.on_selected = partial(self.on_selected_tree_node, node_type=NodeTypes.BEE)
        self.bee_window.setWidget(self.bee_widget)
        self.bee_widget.load_items(found_bees)

    def show_hive_edit_menu(self, path, event):
        # Can only edit .hivemaps
        hivemap_file_path = import_path_to_module_file_path(path)

        if not hivemap_file_path.endswith(".hivemap"):
            return

        menu = QMenu(self.hive_widget)
        edit_action = menu.addAction("Edit Hivemap")

        called_action = menu.exec_(self.mapToGlobal(event.pos()))

        if called_action == edit_action:
            view = self._open_file(hivemap_file_path)

    def open_file(self):
        dialogue = QFileDialog(self, caption="Open Hivemap")
        dialogue.setDefaultSuffix("hivemap")
        dialogue.setNameFilter(dialogue.tr("Hivemaps (*.hivemap)"))
        dialogue.setFileMode(QFileDialog.AnyFile)
        dialogue.setAcceptMode(QFileDialog.AcceptOpen)

        if not dialogue.exec_():
            return

        file_name = dialogue.selectedFiles()[0]
        self._open_file(file_name)

    def _open_file(self, file_name):
        # Check if already open
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)

            if not isinstance(widget, NodeEditorSpace):
                continue

            # If already open
            if file_name == widget.file_name:
                self.tab_widget.setCurrentIndex(index)
                break

        else:
            editor = self.add_editor_space(file_name=file_name)

            # Rename tab
            name = os.path.basename(file_name)
            index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(index, name)

        # Update save UI elements now we have a filename
        self.update_ui_layout()

    def save_as_file(self):
        dialogue = QFileDialog(self, caption="Save Hivemap")
        dialogue.setDefaultSuffix("hivemap")
        dialogue.setNameFilter(dialogue.tr("Hivemaps (*.hivemap)"))
        dialogue.setFileMode(QFileDialog.AnyFile)
        dialogue.setAcceptMode(QFileDialog.AcceptSave)

        if dialogue.exec_():
            file_name = dialogue.selectedFiles()[0]
            self._save_file(file_name=file_name)

            # Refresh hives
            if self.project_directory is not None:
                self.refresh_project_tree()

    def save_file(self, *, file_name=None):
        self._save_file(file_name)

    def _save_file(self, file_name=None):
        widget = self.tab_widget.currentWidget()
        assert isinstance(widget, NodeEditorSpace)

        widget.save(file_name=file_name)

        # Newly saved
        if file_name is not None:
            # Rename tab
            name = os.path.basename(file_name)
            index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(index, name)

            # Update save UI elements now we have a filename
            self.update_ui_layout()
