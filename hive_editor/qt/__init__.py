try:
    import PyQt4
    IS_PYSIDE = False

except ImportError:
    import PySide
    IS_PYSIDE = True