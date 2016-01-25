# Import PySide classes
import ctypes
import sys

import editor.qt as any_qt
import editor.qt.qdarkstyle as qdarkstyle
from editor.qt.main_window import MainWindow
from editor.qt.qt_gui import *

if __name__ == "__main__":
    # Create a Qt application
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(pyside=any_qt.IS_PYSIDE))

    # Fix for windows tray icon
    app_id = 'hive2.hive2.1.0'
    try:
        windll = ctypes.windll

    except AttributeError:
        pass

    else:
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    window = MainWindow()
    window.resize(1024, 768)

    window.show()

    # Enter Qt application main loop
    app.exec_()
    sys.exit()
