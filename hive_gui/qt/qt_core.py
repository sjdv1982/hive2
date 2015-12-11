try:
    from PySide.QtCore import *

    def COMPAT_QT_do_intersection(line_a, line_b):
        return line_a.intersect(line_b)

    Signal = pysideSignal

except ImportError:
    from PyQt4.QtCore import *

    def COMPAT_QT_do_intersection(line_a, line_b):
        point = QPointF()
        result = line_a.intersect(line_b, point)
        return result, point

    Signal = pyqtSignal