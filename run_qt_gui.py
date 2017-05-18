# Import PySide classes
import ctypes
import sys
from logging import getLogger, StreamHandler, Formatter, DEBUG

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from qdarkstyle import load_stylesheet_pyqt5
from hive_editor.qt.main_window import MainWindow


# Setup logging
logger = getLogger()
handler = StreamHandler()
formatter = Formatter('%(asctime)s %(name)-12s %(levelname)-5s %(message)s', datefmt='%I:%M:%S %p')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(DEBUG)


if __name__ == "__main__":
    # Create a Qt application
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet_pyqt5())

    # Fix for windows tray icon
    app_id = 'hive2.hive2.1.0'
    try:
        windll = ctypes.windll

    except AttributeError:
        pass

    else:
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    window = MainWindow()
    window.setWindowState(Qt.WindowMaximized)

    window.show()

    # Enter Qt application main loop
    app.exec_()
    sys.exit()
