# Import PySide classes
import sys
import os

UI = 1

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

    import hive

    from hive_gui.factory import HiveInspector

    insp = HiveInspector()

    inspector = insp.inspect_hive("dragonfly.std.Buffer")


    result = None
    while True:
        try:
            stage_name, stage_options = inspector.send(result)

        except StopIteration:
            break

        print("Options for {}".format(stage_name))
        for option in stage_options:
            print("\t{}={}".format(option[0], option[2]))

        if stage_name == "meta_args":
            result = dict(data_type=("int",), mode="pull")
        else:
            pass

