import os
import webbrowser
import subprocess

from sys import executable as EXECUTABLE_PATH
from os import path
from functools import partial

from PyQt5.QtCore import Qt, QUrl, QStringListModel
from PyQt5.QtWidgets import (QMainWindow, QStatusBar, QAction, QDialog, QMessageBox, QFileDialog, QCompleter, QLineEdit,
                             QHBoxLayout, QMenu, QDockWidget, QLabel)
from PyQt5.QtGui import QIcon, QKeySequence

from .debugging import QtNetworkDebugManager
from .node_editor import NodeEditorSpace
from .tabs import TabViewWidget
from .tree import TreeWidget
from .web_view import QEditorWebView

from .. import tools
from ..finder import all_bees, HiveFinder
from ..importer import clear_imported_hivemaps, sys_path_add_context, module_is_hivemap
from ..node import NodeTypes
from ..utils import find_file_path_of_hive_path


def dict_to_delimited(data, delimiter, name_path=()):
    """Convert a nested dictionary to a sequence of delimited strings.

    :param data: dictionary object
    :param delimiter: delimiter string
    :param name_path: root for all paths e.g ('some', 'root)
    """
    for name, value in data.items():
        new_name_path = name_path + (name,)

        if isinstance(value, dict):
            for sub_value in dict_to_delimited(value, delimiter, new_name_path):
                yield sub_value

        elif value is None:
            yield '.'.join(new_name_path)


class ContextAdaptor:

    class _States:
        null = 0
        inside = 1
        outside = 2

    def __init__(self, context):
        self._context = context
        self._state = self._States.null

    def enter(self):
        if self._state is not self._States.null:
            raise RuntimeError("Context invalid")

        self._state = self._States.inside
        self._context.__enter__()

    def exit(self):
        if self._state is not self._States.inside:
            raise RuntimeError("Context invalid")

        self._state = self._States.outside
        self._context.__exit__(None, None, None)


class MainWindow(QMainWindow):
    _projectNameTemplate = "Hive Node Editor - {}"
    _hivemapExtension = "hivemap"
    _untitledFileName = "<Unsaved>"
    _noProjectText = "<No Project>"

    def __init__(self):
        super(MainWindow, self).__init__()

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self.setDockNestingEnabled(True)
        self.setWindowTitle(self._projectNameTemplate.format(self._noProjectText))

        self.debugger = QtNetworkDebugManager()
        self.debugger.on_closed_session.subscribe(self._onClosedDebugSession)
        self.debugger.on_created_session.subscribe(self._onCreatedDebugSession)

        # Add tab widget
        self.tab_widget = TabViewWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab_widget.onTabChanged.connect(self._onTabChanged)
        self.tab_widget.checkTabClosable = self._checkTabClosable

        # Show current hives
        self._project_hives_active_widget = TreeWidget()
        self._project_hives_active_widget.onDoubleClick.connect(self._openProjectHive)

        self._project_hives_inactive_widget = QLabel("No project active")
        self._project_hives_inactive_widget.setAlignment(Qt.AlignCenter)
        self._project_hives_window = self.createSubwindow("Project", "right",
                                                          widget=self._project_hives_inactive_widget)

        self.hive_finder = HiveFinder()
        self._current_hive_list = None

        self._projectDirectory = None
        self._project_context = None

        self.updateLoadedHives()

        self._setupMenus()

        self._clipboard = None

        # Set application icon
        icon = QIcon()
        file_path = os.path.join(os.path.dirname(__file__), "../hive.png")
        icon.addFile(file_path)
        self.setWindowIcon(icon)

        # Add Help page
        web_view = QEditorWebView()
        web_view.onDragMove.connect(self._filterWebDrop)
        web_view.onDropped.connect(self._onDropped)

        url = QUrl("http://agoose77.github.io/hive2/")
        web_view.setUrl(url)

        # Load home page
        self._web_view = web_view
        self.tab_widget.addTab(web_view, "About", closeable=False)

    def _setupMenus(self):
        menu_bar = self.menuBar()

        self.newAction = QAction("&New", menu_bar, shortcut=QKeySequence.New, statusTip="Create a new file",
                                  triggered=self.addEditorSpace)
        self.loadAction = QAction("&Open...", menu_bar, shortcut=QKeySequence.Open, statusTip="Open an existing file",
                                   triggered=self.openFile)
        self.saveAction = QAction("&Save", menu_bar, shortcut=QKeySequence.Save, statusTip="Save as existing new file",
                                   triggered=self.saveFile)
        self.saveAsAction = QAction("&Save As...", menu_bar, shortcut=QKeySequence.SaveAs,
                                    statusTip="Save as a new file", triggered=self.saveAsFile)

        self.fileMenu = QMenu("&File")
        self.openProjectAction = QAction("Open Project", menu_bar, statusTip="Open an existing Hive project",
                                           triggered=self.openProject, shortcut=QKeySequence("CTRL+SHIFT+O"))
        self.closeProjectAction = QAction("Close Project", menu_bar, statusTip="Close the current Hive project",
                                            triggered=self.closeProject)
        self.refreshProjectAction = QAction("Reload Project", menu_bar, statusTip="Reload the current project",
                                              triggered=self.reloadProject, shortcut=QKeySequence("F5"))
        self.insertAction = QAction("&Insert", menu_bar, statusTip="Insert node from path", triggered=self.insertFromPath)
        self.insertAction.setShortcuts((QKeySequence(Qt.Key_Enter), QKeySequence(Qt.Key_Insert)))
        self.selectAllAction = QAction("Select &All", menu_bar, shortcut=QKeySequence.SelectAll,
                                       statusTip="Select all nodes", triggered=self.selectAllOperation)
        self.undoAction = QAction("&Undo", menu_bar, shortcut=QKeySequence.Undo, statusTip="Undo last operation",
                                   triggered=self.undoOperation)
        self.redoAction = QAction("&Redo", menu_bar, shortcut=QKeySequence.Redo, statusTip="Redo last operation",
                                   triggered=self.redoOperation)
        self.copyAction = QAction("&Copy", menu_bar, shortcut=QKeySequence.Copy, statusTip="Copy selected nodes",
                                   triggered=self.copyOperation)
        self.cutAction = QAction("Cu&t", menu_bar, shortcut=QKeySequence.Cut, statusTip="Cut selected nodes",
                                  triggered=self.cutOperation)
        self.pasteAction = QAction("&Paste", menu_bar, shortcut=QKeySequence.Paste, statusTip="Paste selected nodes",
                                    triggered=self.pasteOperation)

        self.editMenu = QMenu("&Edit")

        self.viewMenu = QMenu("&View")
        self.viewMenu.addAction(self._project_hives_window.toggleViewAction())

        self.runMenu = QMenu("&Run")
        self.runPandaAction = QAction("Launch &Panda3D", menu_bar,
                                      shortcut=QKeySequence(self.tr("CTRL+P", "Launch  in Panda3D")),
                                      triggered=self._launchPanda3D)
        self.runMenu.addAction(self.runPandaAction)

        self.helpAction = QAction("&Help", menu_bar, statusTip="Open Help page in browser",
                                   triggered=self.gotoHelpPage)

    def _openProjectHive(self, reference_path):
        hivemap_file_path = find_file_path_of_hive_path(reference_path)
        self._openFile(hivemap_file_path)

    def _filterWebDrop(self, event):
        """Filter drop events for web view"""
        mime_data = event.mimeData()

        if {'text/uri-list', 'text/plain'}.intersection(mime_data.formats()):
            event.accept()

        else:
            event.ignore()

    def _onDropped(self, event, position):
        mime_data = event.mimeData()

        if mime_data.hasFormat('text/uri-list'):
            file_paths = [u.toLocalFile() for u in mime_data.urls()]

            for file_path in file_paths:
                # If its a folder, try loading project
                if os.path.isdir(file_path):
                    reply = QMessageBox.warning(self, 'Open Project', "A directory was dropped onto the editor, "
                                                                      "attempt to load project?",
                                                QMessageBox.Yes, QMessageBox.No)

                    if reply != QMessageBox.Yes:
                        return

                    self._openProject(file_path)

                else:
                    self._openFile(file_path)

        elif mime_data.hasFormat('text/plain'):
            hivemap_text = mime_data.text()

            editor = self.addEditorSpace()
            editor.loadFromText(hivemap_text)

        else:
            raise TypeError

    def _launchPanda3D(self):
        """Execute Hivemap inside a Panda hive"""
        interpreter_path = EXECUTABLE_PATH
        editor = self.tab_widget.currentWidget()

        hivemap_path = editor.filePath()

        if hivemap_path is None:
            raise ValueError("Need saved hivemap file to launch in Panda3D")

        if editor.hasUnsavedChanges():
            reply = QMessageBox.warning(self, 'Run in Panda3D', "This file has unsaved changes! Are you sure want "
                                                                "to run the old copy?",
                                        QMessageBox.Yes, QMessageBox.No)

            if reply != QMessageBox.Yes:
                return False

        launch_path = path.join(tools.__path__[0], "launch_panda.py")
        commands = [interpreter_path, launch_path, hivemap_path, "debug"]
        from sys import stderr, stdout
        process = subprocess.Popen(commands, stderr=stderr, stdout=stdout)

    def closeEvent(self, event):
        try:
            self.closeOpenTabs()

        except PermissionError:
            event.ignore()

        else:
            event.accept()

    def projectDirectory(self):
        return self._projectDirectory

    def _getDisplayName(self, file_path, allow_untitled=True):
        if file_path is None:
            if not allow_untitled:
                raise ValueError("File name must not be None")

            return self._untitledFileName

        return os.path.basename(file_path)

    def gotoHelpPage(self):
        webbrowser.open("https://github.com/agoose77/hive2/wiki")

    def selectAllOperation(self):
        editor = self.tab_widget.currentWidget()
        editor.selectAll()

    def undoOperation(self):
        editor = self.tab_widget.currentWidget()
        editor.undo()

    def redoOperation(self):
        editor = self.tab_widget.currentWidget()
        editor.redo()

    def copyOperation(self):
        editor = self.tab_widget.currentWidget()
        self._clipboard = editor.copy()

    def cutOperation(self):
        editor = self.tab_widget.currentWidget()
        self._clipboard = editor.cut()

    def pasteOperation(self):
        editor = self.tab_widget.currentWidget()
        clipboard = self._clipboard

        if clipboard is not None:
            editor.paste(clipboard)

    def _checkTabClosable(self, index):
        widget = self.tab_widget.widget(index)

        if widget.hasUnsavedChanges():
            reply = QMessageBox.warning(self, 'Close File', "This file has unsaved changes. Do you want to close it?",
                                        QMessageBox.Yes, QMessageBox.No)

            if reply != QMessageBox.Yes:
                return False

        # Stop debugging if editor is closed
        if self.debugger.session is not None:
            file_path = widget.filePath()

            if file_path:
                if self.debugger.session.is_debugging_hivemap(file_path):
                    self.debugger.session.close()

        widget.onExit()
        return True

    def _onTabChanged(self, previous_index=None):
        tab_widget = self.tab_widget

        # Exit last open view
        if previous_index is not None:
            previous_widget = tab_widget.widget(previous_index)
            if isinstance(previous_widget, NodeEditorSpace):
                previous_widget.onExit()

        # Update UI elements
        self._updateMenuOptions()

        widget = tab_widget.currentWidget()

        # Replace docstring
        if isinstance(widget, NodeEditorSpace):
            widget.onEnter()

    def addEditorSpace(self, *_, file_path=None):
        editor = NodeEditorSpace(file_path, project_path=self._projectDirectory)

        display_name = self._getDisplayName(file_path)
        index = self.tab_widget.addTab(editor, display_name)
        self.tab_widget.setCurrentIndex(index)

        editor.onSaveStateUpdated.connect(partial(self.onSaveStateChanged, editor))
        editor.doOpenFile.connect(self._openFile)
        editor.onDroppedForParent.connect(self._onDropped)

        editor.updateBeeTree(all_bees)
        editor.updateHiveTree(self.hive_finder.all_hives)

        # Ask to handle these
        editor.setParentDropMimeTypes({'text/uri-list', 'text/plain'})

        return editor

    def createSubwindow(self, title, position, closeable=True, widget=None):
        area_classes = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea,
        }
        area = area_classes[position]

        window = QDockWidget(title, self)
        features = QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable
        if closeable:
            features |= QDockWidget.DockWidgetClosable

        window.setFeatures(features)
        if widget is not None:
            window.setWidget(widget)

        self.addDockWidget(area, window)
        return window

    def _updateMenuOptions(self):
        show_save = False
        show_save_as = False

        menu_bar = self.menuBar()
        menu_bar.clear()

        menu_bar.addMenu(self.fileMenu)
        self.fileMenu.clear()

        menu_bar.addMenu(self.editMenu)
        self.editMenu.clear()

        self.fileMenu.addAction(self.openProjectAction)

        if self._projectDirectory is not None:
            self.fileMenu.addAction(self.refreshProjectAction)
            self.fileMenu.addAction(self.closeProjectAction)

        widget = self.tab_widget.currentWidget()

        is_node_editor = isinstance(widget, NodeEditorSpace)
        if is_node_editor:
            show_save_as = True
            show_save = widget.filePath() is not None

            self.fileMenu.addAction(self.insertAction)
            menu_bar.addMenu(self.runMenu)

            self.editMenu.addAction(self.selectAllAction)
            self.editMenu.addSeparator()
            self.editMenu.addAction(self.undoAction)
            self.editMenu.addAction(self.redoAction)
            self.editMenu.addSeparator()
            self.editMenu.addAction(self.cutAction)
            self.editMenu.addAction(self.copyAction)
            self.editMenu.addAction(self.pasteAction)
            self.editMenu.addSeparator()

        self.saveAction.setVisible(show_save)
        self.saveAsAction.setVisible(show_save_as)

        self.fileMenu.addAction(self.newAction)
        self.fileMenu.addAction(self.loadAction)

        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.saveAsAction)

        menu_bar.addMenu(self.viewMenu)
        menu_bar.addAction(self.helpAction)

    def insertFromPath(self):
        dialogue = QDialog(self)
        layout = QHBoxLayout()
        dialogue.setLayout(layout)

        editor = QLineEdit()
        layout.addWidget(editor)

        completer = QCompleter()
        completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)

        editor.setCompleter(completer)

        model = QStringListModel()
        completion_paths = self.hive_finder.all_hives
        model.setStringList(completion_paths)

        completer.setModel(model)

        def on_return():
            widget = self.tab_widget.currentWidget()

            if not isinstance(widget, NodeEditorSpace):
                return

            reference_path = editor.text()
            widget.addNodeAtMouse(reference_path, NodeTypes.HIVE)
            dialogue.close()

        editor.returnPressed.connect(on_return)

        dialogue.setWindowTitle("Add Hive From Path")
        dialogue.setAttribute(Qt.WA_DeleteOnClose)
        dialogue.exec_()

    def openProject(self):
        dialogue = QFileDialog(self, caption="Open Hive Project")
        dialogue.setFileMode(QFileDialog.DirectoryOnly)
        dialogue.setAcceptMode(QFileDialog.AcceptOpen)
        dialogue.setOption(QFileDialog.ShowDirsOnly)

        if not dialogue.exec_():
            return

        directory_path = dialogue.selectedFiles()[0]
        self._openProject(directory_path)

    def reloadProject(self):
        directory = self._projectDirectory
        self._openProject(directory)

    def _openProject(self, directory_path):
        # Close existing tabs
        self.closeProject()

        # Load HIVES from project
        self.hive_finder.additional_paths = {directory_path, }

        # Set directory
        self._projectDirectory = directory_path

        # Enter import context
        assert self._project_context is None, "Import context should be None!"
        project_context_manager = sys_path_add_context(directory_path)

        self._project_context = ContextAdaptor(project_context_manager)
        self._project_context.enter()

        self.updateLoadedHives()
        self._updateMenuOptions()

        # Rename window project
        self.setWindowTitle(self._projectNameTemplate.format(directory_path))

        # Update hives display in project window
        self._project_hives_window.setWidget(self._project_hives_active_widget)
        hives_in_project = self.hive_finder.hives_by_path[directory_path]
        project_hivemaps = [p for p in hives_in_project if module_is_hivemap(__import__(p.rsplit('.', 1)[0]))]
        self._project_hives_active_widget.setItems(project_hivemaps)

    def closeOpenTabs(self):
        while self.tab_widget.count() > 1:
            self.tab_widget.removeTab(1)

    def closeProject(self):
        # Close open tabs
        self.closeOpenTabs()

        # If project was open
        if self._project_context:
            self._project_context.exit()
            self._project_context = None
            clear_imported_hivemaps()

            self.hive_finder.additional_paths.clear()
            self._projectDirectory = None

        # Rename window project
        self.setWindowTitle(self._projectNameTemplate.format(self._noProjectText))

        self.updateLoadedHives()
        self._updateMenuOptions()

        self._project_hives_window.setWidget(self._project_hives_inactive_widget)

    def updateLoadedHives(self):
        """Update the hive list in loaded editors"""
        self.hive_finder.reload()

        hives = self.hive_finder.all_hives
        bees = all_bees

        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)

            if isinstance(widget, NodeEditorSpace):
                widget.updateHiveTree(hives)
                widget.updateBeeTree(bees)

    def showHiveEditMenu(self, hive_widget, reference_path, event):
        try:
            hivemap_file_path = find_file_path_of_hive_path(reference_path)

        except ValueError:
            return

        menu = QMenu(hive_widget)
        editAction = menu.addAction("Edit Hivemap")
        global_position = hive_widget.mapToGlobal(event.pos())
        calledAction = menu.exec_(global_position)

        if calledAction == editAction:
            self._openFile(hivemap_file_path)

    def onSaveStateChanged(self, editor, has_unsaved_changes):
        # Check if already open
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            if widget is editor:
                break

        else:
            raise ValueError()

        file_path = self._getDisplayName(editor.filePath())

        if not has_unsaved_changes:
            self.tab_widget.setTabText(index, file_path)

        else:
            self.tab_widget.setTabText(index, "{}*".format(file_path))

    def findEditorOfFile(self, file_path):
        """Find open editor of file path.
        Raise ValueError if no editor is found.

        :param file_path: path of file
        """
        # Check if already open
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            if not isinstance(widget, NodeEditorSpace):
                continue

            widget_file_path = widget.filePath()
            if widget_file_path is None:
                continue

            # If already open
            if os.path.samefile(file_path, widget_file_path):
                return widget

        raise ValueError("File not open")

    def openFile(self):
        dialogue = QFileDialog(self, caption="Open Hivemap")
        dialogue.setDefaultSuffix(self._hivemapExtension)
        dialogue.setNameFilter(dialogue.tr("Hivemaps (*.{})".format(self._hivemapExtension)))
        dialogue.setFileMode(QFileDialog.AnyFile)
        dialogue.setAcceptMode(QFileDialog.AcceptOpen)

        if not dialogue.exec_():
            return

        file_path = dialogue.selectedFiles()[0]
        self._openFile(file_path)

    def _openFile(self, file_path):
        # Check if already open
        try:
            editor = self.findEditorOfFile(file_path)
            self.tab_widget.setCurrentWidget(editor)

        except ValueError:
            editor = self.addEditorSpace(file_path=file_path)

            # Rename tab
            name = self._getDisplayName(file_path, allow_untitled=False)
            index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(index, name)

        # Update save UI elements now we have a filename
        self._updateMenuOptions()
        return editor

    def saveAsFile(self):
        widget = self.tab_widget.currentWidget()
        assert isinstance(widget, NodeEditorSpace)

        dialogue = QFileDialog(self, caption="Save Hivemap")
        dialogue.setDefaultSuffix(self._hivemapExtension)
        dialogue.setNameFilter(dialogue.tr("Hivemaps (*.{})".format(self._hivemapExtension)))
        dialogue.setFileMode(QFileDialog.AnyFile)
        dialogue.setAcceptMode(QFileDialog.AcceptSave)

        if not dialogue.exec_():
            return

        file_path = dialogue.selectedFiles()[0]

        widget.save(file_path=file_path)
        widget.setFilePath(file_path)

        # Update tab name
        name = self._getDisplayName(file_path, allow_untitled=False)
        index = self.tab_widget.currentIndex()
        self.tab_widget.setTabText(index, name)

        # Update save UI elements (filename may have changed) filename
        self._updateMenuOptions()

        # Refresh hives
        if self._projectDirectory is not None:
            self.updateLoadedHives()

    def saveFile(self):
        widget = self.tab_widget.currentWidget()
        assert isinstance(widget, NodeEditorSpace)
        widget.save()

    def _onCreatedDebugController(self, debug_controller):
        editor = self._openFile(debug_controller.file_path)
        editor.onDebuggingStarted(debug_controller)

    def _onDestroyedDebugController(self, debug_controller):
        editor = self.findEditorOfFile(debug_controller.file_path)
        editor.onDebuggingFinished()

    def _onCreatedDebugSession(self, debug_session):
        debug_session.on_created_controller.subscribe(self._onCreatedDebugController)
        debug_session.on_destroyed_controller.subscribe(self._onDestroyedDebugController)

    def _onClosedDebugSession(self, debug_session):
        debug_session.on_created_controller.unsubscribe(self._onCreatedDebugController)
        debug_session.on_destroyed_controller.unsubscribe(self._onDestroyedDebugController)
