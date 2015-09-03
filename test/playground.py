# Import PySide classes
import sys
import os

UI = False

if UI:
    from PySide.QtGui import *
    from PySide.QtWebKit import *

    import hive_gui.pyside as py_gui
    p = sys.path.copy()
    sys.path.insert(0, py_gui.__path__[0])

    import qdarkstyle as qdarkstyle
    sys.path[:] = p

    from hive_gui.pyside.main_window import MainWindow

    from hive_gui.finder import get_hives
    import sca as test_sca
    import dragonfly

    # Create a Qt application
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    hives = get_hives(test_sca, dragonfly)

    window = MainWindow()
    window.resize(480, 320)

    window.show()

    bees = {"hive": ["antenna", "output", "entry", "hook", "triggerfunc", "modifier",
                     "pull_in", "pull_out", "push_in", "push_out", "attribute"]}

    #helpers = {"helpers": ["trigger_in", "trigger_out"]}

    window.hive_widget.load_items(hives)
    window.bee_widget.load_items(bees)
    #window.helper_widget.load_items(helpers)

    # Add Help page
    home_page = QWebView()

    # Load Help data
    local_dir = py_gui.__path__[0]
    html_file_name = os.path.join(local_dir, "home.html")

    with open(html_file_name) as f:
        html = f.read().replace("%LOCALDIR%", local_dir)

    home_page.setHtml(html)

    window.load_home_page(home_page)



    # Enter Qt application main loop
    app.exec_()
    sys.exit()

else:
    # with open("C:/users/angus/desktop/some_hive.hivemap") as f:
    #     hm =f.read()
    #
    # from hive_gui.utils import builder_from_hivemap
    # b = builder_from_hivemap(hm)

    import hive
    s="""

def builder(i, ex, args):

    # Imports
    import hive
    import dragonfly

    # Declarations
    i.a = dragonfly.std.Variable(data_type=('int',), start_value=1)
    i.Op_0 = dragonfly.op.Op(data_type='int', operator= 'add', mode='pull', default_value=0)
    ex.score = hive.attribute(('int',), 0)
    i.pull_in_0 = hive.pull_in(ex.score)
    i.pull_out_0 = hive.pull_out(ex.score)

    # Connectivity
    hive.connect(i.a.value, i.Op_0.a)
    hive.connect(i.Op_0.c, i.pull_in_0)
    hive.connect(i.pull_out_0, i.Op_0.b)

    # IO
    ex.trig_out = hive.hook(i.pull_in_0)
    ex.trig_in = hive.entry(i.pull_in_0)

"""
    exec(s, locals(), globals())
    h = hive.hive("H", builder)
    hh=h()

    for i in range(5):
        hh.trig_in()
        print(hh.score)