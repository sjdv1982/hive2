# Import PySide classes
import sys
import os

from PySide.QtGui import *
from PySide.QtWebKit import *

import hive_gui.pyside as py_gui

from hive_gui.pyside.main_window import MainWindow

from hive_gui.finder import get_hives
import sca as test_sca
import dragonfly

# Create a Qt application
app = QApplication(sys.argv)

hives = get_hives(test_sca, dragonfly)

window = MainWindow()
window.resize(480, 320)

window.show()
window.hive_tree.load_hives(hives)

# Add Help page
home_page = QWebView()

# Load Help data
html_file_name = os.path.join(py_gui.__path__[0], "home.html")
with open(html_file_name) as f:
    home_page.setHtml(f.read())

window.load_home_page(home_page)


#TODO support configuration of hives before adding


# Enter Qt application main loop
app.exec_()
sys.exit()