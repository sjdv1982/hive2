import hive
import hive_gui.utils as utils
#
# MyHive = utils.class_from_filepath("D:/hivedemo/my_iter.hivemap")
#
# my_hive = MyHive()
# my_hive.do_iter()
#
MyHive = utils.class_from_filepath("D:/hivedemo/example.hivemap")

my_hive = MyHive()
print("BEFORE")
my_hive.start_counting()
print("AFTER")
