# Import PySide classes
import sys
import os

from PySide.QtGui import *
from PySide.QtWebKit import *

import hive_gui.pyside as pyside_gui
import hive_gui.pyside.qdarkstyle as qdarkstyle

from hive_gui.pyside.main_window import MainWindow
from hive_gui.finder import get_hives

import dragonfly

# Create a Qt application
app = QApplication(sys.argv)
app.setStyleSheet(qdarkstyle.load_stylesheet())

hives = get_hives(dragonfly)

window = MainWindow()
window.resize(480, 320)

window.show()

bees = {"hive": ["attribute", "antenna", "output", "entry", "hook", "triggerfunc", "modifier", "pull_in", "pull_out",
                 "push_in", "push_out"]}


window.hive_widget.load_items(hives)
window.bee_widget.load_items(bees)

# Add Help page
home_page = QWebView()

# Load Help data
local_dir = pyside_gui.__path__[0]
html_file_name = os.path.join(local_dir, "home.html")

with open(html_file_name) as f:
    html = f.read().replace("%LOCALDIR%", local_dir)

home_page.setHtml(html)

window.load_home_page(home_page)

# Enter Qt application main loop
app.exec_()
sys.exit()