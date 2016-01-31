import os
import webbrowser
from functools import partial

from .debugger import QtRemoteDebugServer
from .node_editor import NodeEditorSpace
from .qt_core import *
from .qt_gui import *
from .tabs import TabViewWidget
from .tree import TreeWidget
from .web_view import QEditorWebView

from ..finder import found_bees, HiveFinder
from ..importer import clear_imported_hivemaps, get_hook
from ..node import NodeTypes
from ..utils import import_path_to_hivemap_path

area_classes = {
    "left": Qt.LeftDockWidgetArea,
    "right": Qt.RightDockWidgetArea,
    "top": Qt.TopDockWidgetArea,
    "bottom": Qt.BottomDockWidgetArea,
}


def dict_to_delimited(data, delimiter, name_path=()):
    for name, value in data.items():
        new_name_path = name_path + (name,)

        if isinstance(value, dict):
            yield from dict_to_delimited(value, delimiter, new_name_path)

        elif value is None:
            yield '.'.join(new_name_path)


class MainWindow(QMainWindow):
    project_name_template = "Hive Node Editor - {}"
    hivemap_extension = ".hivemap"
    untitled_file_name = "<Unsaved>"

    def __init__(self):
        QMainWindow.__init__(self)

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self._setup_windows()
        self._setup_menus()

        self.debugger = QtRemoteDebugServer()

        self.hive_finder = HiveFinder()

        self.project_directory = None
        self._project_context = None

        self._pending_dropped_node_info = None
        self.refresh_project_tree()

        self._clipboard = None

        # Set application icon
        icon = QIcon()
        file_path = os.path.join(os.path.dirname(__file__), "images/hive.png")
        icon.addFile(file_path)
        self.setWindowIcon(icon)

        # Add Help page
        web_view = QEditorWebView()
        web_view.on_drag_enter = self._web_on_drag_enter

        USE_LOCAL_HOME = True

        if USE_LOCAL_HOME:
            # Load Help data
            local_dir = os.path.dirname(__file__)
            html_file_name = os.path.join(local_dir, "home.html")

            with open(html_file_name) as f:
                html = f.read().replace("%LOCALDIR%", local_dir)

            web_view.setHtml(html)
        else:
            url = QUrl("https://github.com/agoose77/hive2/wiki")
            web_view.load(url)

        # Load home page
        self._web_view = web_view
        self.tab_widget.addTab(web_view, "About", closeable=False)

    def _setup_menus(self):
        menu_bar = self.menuBar()
        self.new_action = QAction("&New", menu_bar, shortcut=QKeySequence.New, statusTip="Create a new file",
                                  triggered=self.add_editor_space)
        self.load_action = QAction("&Open...", menu_bar, shortcut=QKeySequence.Open, statusTip="Open an existing file",
                                   triggered=self.open_file)
        self.save_action = QAction("&Save", menu_bar, shortcut=QKeySequence.Save, statusTip="Save as existing new file",
                                   triggered=self.save_file)
        self.save_as_action = QAction("&Save As...", menu_bar, shortcut=QKeySequence.SaveAs,
                                      statusTip="Save as a new file", triggered=self.save_as_file)

        self.file_menu = QMenu("&File")
        self.open_project_action = QAction("Open Project", menu_bar, statusTip="Open an existing Hive project",
                                           triggered=self.open_project)
        self.close_project_action = QAction("Close Project", menu_bar, statusTip="Close the current Hive project",
                                            triggered=self.close_project)
        self.refresh_project_action = QAction("Reload Project", menu_bar, statusTip="Reload the current project",
                                              triggered=self.reload_project)
        self.insert_action = QAction("&Insert", menu_bar, shortcut=QKeySequence(self.tr(".", "  Insert from path")),
                                     statusTip="Insert node from path", triggered=self.insert_from_path)
        self.select_all_action = QAction("Select &All", menu_bar, shortcut=QKeySequence.SelectAll,
                                         statusTip="Select all nodes", triggered=self.select_all_operation)
        self.undo_action = QAction("&Undo", menu_bar, shortcut=QKeySequence.Undo, statusTip="Undo last operation",
                                   triggered=self.undo_operation)
        self.redo_action = QAction("&Redo", menu_bar, shortcut=QKeySequence.Redo, statusTip="Redo last operation",
                                   triggered=self.redo_operation)
        self.copy_action = QAction("&Copy", menu_bar, shortcut=QKeySequence.Copy, statusTip="Copy selected nodes",
                                   triggered=self.copy_operation)
        self.cut_action = QAction("Cu&t", menu_bar, shortcut=QKeySequence.Cut, statusTip="Cut selected nodes",
                                  triggered=self.cut_operation)
        self.paste_action = QAction("&Paste", menu_bar, shortcut=QKeySequence.Paste, statusTip="Paste selected nodes",
                                    triggered=self.paste_operation)

        self.edit_menu = QMenu("&Edit")

        self.edit_menu.addAction(self.select_all_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.cut_action)
        self.edit_menu.addAction(self.copy_action)
        self.edit_menu.addAction(self.paste_action)

        self.view_menu = QMenu("&View")

        # Allow minimisable
        self.view_menu.addAction(self.hive_window.toggleViewAction())
        self.view_menu.addAction(self.bee_window.toggleViewAction())
        self.view_menu.addAction(self.folding_window.toggleViewAction())
        self.view_menu.addAction(self.configuration_window.toggleViewAction())
        self.view_menu.addAction(self.console_window.toggleViewAction())
        self.view_menu.addAction(self.preview_window.toggleViewAction())

        self.help_action = QAction("&Help", menu_bar, statusTip="Open Help page in browser",
                                   triggered=self.goto_help_page)

    def _setup_windows(self):
        self.setDockNestingEnabled(True)

        # Add tab widget
        self.tab_widget = TabViewWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab_widget.on_changed = self._on_tab_changed
        self.tab_widget.check_tab_closable = self._check_tab_closable

        # Left window
        self.bee_window = self.create_subwindow("Bees", "left", closeable=True)

        # Left window
        self.hive_window = self.create_subwindow("Hives", "left", closeable=True)

        # Docstring editor
        self.configuration_window = self.create_subwindow("Configuration", "right", closeable=True)
        self.folding_window = self.create_subwindow("Folding", "right", closeable=True)
        self.preview_window = self.create_subwindow("Preview", "left", closeable=True)
        self.docstring_window = self.create_subwindow("Docstring", "left", closeable=True)
        self.console_window = self.create_subwindow("Console", "bottom", closeable=True)
        self.breakpoints_window = self.create_subwindow("Breakpoints", "bottom", closeable=True)

        self.breakpoints_list = QListWidget()
        self.breakpoints_window.setWidget(self.breakpoints_list)

        # Make tabs
        self.tabifyDockWidget(self.bee_window, self.hive_window)
        self.tabifyDockWidget(self.docstring_window, self.preview_window)

    def closeEvent(self, event):
        try:
            self.close_open_tabs()
        except PermissionError:
            event.ignore()
        else:
            event.accept()

    @property
    def project_directory(self):
        return self._project_directory

    @project_directory.setter
    def project_directory(self, value):
        self._project_directory = value

        if value is None:
            directory_name = "<No project>"
        else:
            directory_name = os.path.basename(value)

        # Rename project
        title = self.project_name_template.format(directory_name)
        self.setWindowTitle(title)

    def _get_display_name(self, file_name, allow_untitled=True):
        if file_name is None:
            if not allow_untitled:
                raise ValueError("File name must not be None")

            return self.untitled_file_name

        return os.path.basename(file_name)

    def _get_hivemap_path_in_project(self, import_path):
        if self.project_directory:
            additional_paths = [self.project_directory]

        else:
            additional_paths = []

        return import_path_to_hivemap_path(import_path, additional_paths)

    def goto_help_page(self):
        webbrowser.open("https://github.com/agoose77/hive2/wiki")

    def select_all_operation(self):
        editor = self.tab_widget.currentWidget()
        editor.select_all()

    def undo_operation(self):
        editor = self.tab_widget.currentWidget()
        editor.undo()

    def redo_operation(self):
        editor = self.tab_widget.currentWidget()
        editor.redo()

    def copy_operation(self):
        editor = self.tab_widget.currentWidget()
        self._clipboard = editor.copy()

    def cut_operation(self):
        editor = self.tab_widget.currentWidget()
        self._clipboard = editor.cut()

    def paste_operation(self):
        editor = self.tab_widget.currentWidget()
        clipboard = self._clipboard

        if clipboard is not None:
            editor.paste(clipboard)

    def _check_tab_closable(self, index):
        widget = self.tab_widget.widget(index)

        if widget.has_unsaved_changes:
            reply = QMessageBox.warning(self, 'Close File', "This file has unsaved changes. Do you want to close it?",
                                        QMessageBox.Yes, QMessageBox.No)

            if reply != QMessageBox.Yes:
                return False

        widget.on_exit(self.docstring_window, self.folding_window, self.configuration_window, self.preview_window,
                       self.console_window)
        return True

    def _on_tab_changed(self, tab_menu, previous_index=None):
        # Exit last open view
        if previous_index is not None:
            previous_widget = tab_menu.widget(previous_index)
            if isinstance(previous_widget, NodeEditorSpace):
                previous_widget.on_exit(self.docstring_window, self.folding_window, self.configuration_window,
                                        self.preview_window, self.console_window)

        # Update UI elements
        self._update_ui_layout()

        widget = tab_menu.currentWidget()

        # Replace docstring
        if isinstance(widget, NodeEditorSpace):
            widget.on_enter(self.docstring_window, self.folding_window, self.configuration_window, self.preview_window,
                            self.console_window)

    def add_editor_space(self, *, file_name=None):
        editor = NodeEditorSpace(file_name)

        display_name = self._get_display_name(file_name)

        index = self.tab_widget.addTab(editor, display_name)
        self.tab_widget.setCurrentIndex(index)

        editor.on_update_is_saved = partial(self._on_save_state_changed, editor)
        editor.do_open_file = self._open_file
        editor.get_hivemap_path = self._get_hivemap_path_in_project
        editor.get_dropped_node_info = self._accept_dropped_node_info

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

    def _update_ui_layout(self):
        show_save = False
        show_save_as = False

        show_edit = False

        show_docstring = True
        show_config = True
        show_folding = True
        show_hives = True
        show_bees = True
        show_preview = True
        show_insert = False

        menu_bar = self.menuBar()
        menu_bar.clear()

        menu_bar.addMenu(self.file_menu)
        self.file_menu.clear()

        self.file_menu.addAction(self.open_project_action)

        if self.project_directory is not None:
            self.file_menu.addAction(self.refresh_project_action)
            self.file_menu.addAction(self.close_project_action)

        widget = self.tab_widget.currentWidget()

        file_is_open = isinstance(widget, NodeEditorSpace)
        if file_is_open:
            show_save_as = True
            show_save = widget.file_name is not None
            show_edit = True
            show_insert = True

        self.save_action.setVisible(show_save)
        self.save_as_action.setVisible(show_save_as)

        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.load_action)

        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)

        if show_insert:
            self.file_menu.addAction(self.insert_action)

        menu_bar.addMenu(self.view_menu)


        if show_edit:
            menu_bar.addMenu(self.edit_menu)

        menu_bar.addAction(self.help_action)

        # Static visibilities
        self.docstring_window.setVisible(show_docstring)
        self.folding_window.setVisible(show_folding)
        self.configuration_window.setVisible(show_config)
        self.hive_window.setVisible(show_hives)
        self.bee_window.setVisible(show_bees)
        self.preview_window.setVisible(show_preview)

    def _accept_dropped_node_info(self):
        info, self._pending_dropped_node_info = self._pending_dropped_node_info, None
        return info

    def on_selected_tree_node(self, path, node_type):
        self._pending_dropped_node_info = path, node_type

    def _web_on_drag_enter(self, position):
        if self._pending_dropped_node_info is None:
            return

        # Create blank editor
        self.add_editor_space()

    def insert_from_path(self):
        dialogue = QDialog(self)
        layout = QHBoxLayout()
        dialogue.setLayout(layout)

        editor = QLineEdit()
        layout.addWidget(editor)

        completer = QCompleter()
        completer.setCompletionMode(QCompleter.InlineCompletion)
        completer.setCaseSensitivity(Qt.CaseSensitive)

        editor.setCompleter(completer)

        model = QStringListModel()
        completer.setModel(model)

        completion_paths = list(dict_to_delimited(self.hive_finder.find_hives(), '.'))
        model.setStringList(completion_paths)

        def on_return():
            widget = self.tab_widget.currentWidget()

            if not isinstance(widget, NodeEditorSpace):
                return

            import_path = editor.text()
            widget.add_node_at_mouse(import_path, NodeTypes.HIVE)
            dialogue.close()

        editor.returnPressed.connect(on_return)

        dialogue.setWindowTitle("Add Hive From Path")
        dialogue.setAttribute(Qt.WA_DeleteOnClose)
        dialogue.exec_()

    def open_project(self):
        dialogue = QFileDialog(self, caption="Open Hive Project")
        dialogue.setFileMode(QFileDialog.DirectoryOnly)
        dialogue.setAcceptMode(QFileDialog.AcceptOpen)
        dialogue.setOption(QFileDialog.ShowDirsOnly)

        if not dialogue.exec_():
            return

        directory_path = dialogue.selectedFiles()[0]
        self.close_project()
        self._open_project(directory_path)

    def reload_project(self):
        directory = self.project_directory
        self.close_project()
        self._open_project(directory)

    def _open_project(self, directory_path):
        # Load HIVES from project
        self.hive_finder.additional_paths = {directory_path, }

        # Set directory
        self.project_directory = directory_path

        # Enter import context
        assert self._project_context is None, "Import context should be None!"
        self._project_context = get_hook().temporary_relative_context(directory_path)
        self._project_context.__enter__()

        self.refresh_project_tree()
        self._update_ui_layout()

    def close_open_tabs(self):
        while self.tab_widget.count() > 1:
            self.tab_widget.removeTab(1)

    def close_project(self):
        # Close open tabs
        self.close_open_tabs()

        self.hive_finder.additional_paths.clear()
        self.project_directory = None

        if self._project_context:
            self._project_context.__exit__(None, None, None)
            self._project_context = None

        self.refresh_project_tree()
        self._update_ui_layout()

        clear_imported_hivemaps()

    def refresh_project_tree(self):
        self.hive_widget = TreeWidget(title="Path")
        self.hive_widget.on_selected = partial(self.on_selected_tree_node, node_type=NodeTypes.HIVE)
        self.hive_window.setWidget(self.hive_widget)
        self.hive_widget.load_items(self.hive_finder.find_hives())
        self.hive_widget.on_right_click = self.show_hive_edit_menu

        self.bee_widget = TreeWidget(title="Path")
        self.bee_widget.on_selected = partial(self.on_selected_tree_node, node_type=NodeTypes.BEE)
        self.bee_window.setWidget(self.bee_widget)
        self.bee_widget.load_items(found_bees)

    def show_hive_edit_menu(self, import_path, event):
        # Can only edit .hivemaps
        try:
            hivemap_file_path = self._get_hivemap_path_in_project(import_path)

        except ValueError:
            return

        menu = QMenu(self.hive_widget)
        edit_action = menu.addAction("Edit Hivemap")

        global_position = self.hive_widget.mapToGlobal(event.pos())
        called_action = menu.exec_(global_position)

        if called_action == edit_action:
            editor = self._open_file(hivemap_file_path)

    def _on_save_state_changed(self, editor, has_unsaved_changes):
        # Check if already open
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            if widget is editor:
                break

        else:
            raise ValueError()

        file_name = self._get_display_name(editor.file_name)

        if not has_unsaved_changes:
            self.tab_widget.setTabText(index, file_name)

        else:
            self.tab_widget.setTabText(index, "{}*".format(file_name))

    def open_file(self):
        dialogue = QFileDialog(self, caption="Open Hivemap")
        dialogue.setDefaultSuffix("hivemap")
        dialogue.setNameFilter(dialogue.tr("Hivemaps (*{})".format(self.hivemap_extension)))
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

            widget_file_name = widget.file_name
            if widget_file_name is None:
                continue

            # If already open
            if os.path.samefile(file_name, widget_file_name):
                self.tab_widget.setCurrentIndex(index)
                break

        else:
            editor = self.add_editor_space(file_name=file_name)

            # Rename tab
            name = self._get_display_name(file_name, allow_untitled=False)
            index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(index, name)

        # Update save UI elements now we have a filename
        self._update_ui_layout()

    def save_as_file(self):
        widget = self.tab_widget.currentWidget()
        assert isinstance(widget, NodeEditorSpace)

        dialogue = QFileDialog(self, caption="Save Hivemap")
        dialogue.setDefaultSuffix("hivemap")
        dialogue.setNameFilter(dialogue.tr("Hivemaps (*{})".format(self.hivemap_extension)))
        dialogue.setFileMode(QFileDialog.AnyFile)
        dialogue.setAcceptMode(QFileDialog.AcceptSave)

        if not dialogue.exec_():
            return

        file_name = dialogue.selectedFiles()[0]

        was_untitled = widget.file_name is None
        widget.save(file_name=file_name)

        # Rename tab
        name = self._get_display_name(file_name, allow_untitled=False)
        index = self.tab_widget.currentIndex()
        self.tab_widget.setTabText(index, name)

        # Update save UI elements now we have a filename
        if was_untitled:
            self._update_ui_layout()

        # Refresh hives
        if self.project_directory is not None:
            self.refresh_project_tree()

    def save_file(self):
        widget = self.tab_widget.currentWidget()
        assert isinstance(widget, NodeEditorSpace)
        widget.save()

    # TODO DEBUG on tab closed clear debug info