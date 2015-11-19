from hive_gui.importer import install_hook
install_hook()

folder = "D:/PycharmProjects/hive2/test_fs"

import sys
sys.path.append(folder)


from hive_gui.finder import HiveFinder

hf = HiveFinder(folder)
print(hf.find_hives())