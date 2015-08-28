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

    bees = {"hive": ["antenna", "output", "entry", "hook"]}

    window.hive_widget.load_hives(hives)
    window.bee_widget.load_hives(bees)

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
    hivemap_str = """
Hivemap (
  hives = HiveNodeArray (
    HiveNode (
      identifier = 'Buffer_4',
      import_path = 'dragonfly.std.Buffer',
      position = Coordinate2D (
        x = 332.0,
        y = 129.0,
      ),
      meta_args = HiveInstanceParameterArray (
        HiveInstanceParameter (
          identifier = 'data_type',
          data_type = 'tuple',
          value = "('int',)",
        ),
        HiveInstanceParameter (
          identifier = 'mode',
          data_type = 'str',
          value = 'push',
        ),
      ),
      args = HiveInstanceParameterArray (
        HiveInstanceParameter (
          identifier = 'start_value',
          data_type = 'int',
          value = '0',
        ),
      ),
      cls_args = HiveInstanceParameterArray (
      ),
      folded_pins = StringArray (
      ),
    ),
  ),
  io_bees = IOBeeNodeArray (
    IOBeeNode (
      identifier = 'input_1',
      import_path = 'hive.entry',
      position = Coordinate2D (
        x = 202.85714285714292,
        y = 325.71428571428584,
      ),
    ),
    IOBeeNode (
      identifier = 'input_0',
      import_path = 'hive.antenna',
      position = Coordinate2D (
        x = 49.0,
        y = 229.0,
      ),
    ),
    IOBeeNode (
      identifier = 'output_0',
      import_path = 'hive.output',
      position = Coordinate2D (
        x = 526.0,
        y = 263.0,
      ),
    ),
  ),
  connections = ConnectionArray (
    Connection (
      from_node = 'input_1',
      output_name = 'input',
      to_node = 'Buffer_4',
      input_name = 'trigger',
    ),
    Connection (
      from_node = 'Buffer_4',
      output_name = 'output',
      to_node = 'output_0',
      input_name = 'output',
    ),
    Connection (
      from_node = 'input_0',
      output_name = 'input',
      to_node = 'Buffer_4',
      input_name = 'input',
    ),
  ),
  docstring = '',
)"""

    from hive_gui.utils import class_from_hivemap
    cls = class_from_hivemap("TestHive", hivemap_str)
    h = cls()

    h.input_0.push(12)
    assert h._Buffer_4.value == 12