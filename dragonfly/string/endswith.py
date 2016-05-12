import hive

# TODO future - it might be that this should be given a declarator for "advanced mode", and by default
# Just use a normal argument to define the substring


def do_endswith(self):
    self._endswith = self._string.endswith(self._substring)


def build_endswith(i, ex, args):
    """Check if string ends with a substring"""
    i.string = hive.attribute('str')
    i.substring = hive.attribute('str')

    i.pull_string = hive.pull_in(i.string)
    i.pull_substring = hive.pull_in(i.substring)

    ex.string = hive.antenna(i.pull_string)
    ex.substring = hive.antenna(i.pull_substring)

    i.endswith = hive.attribute('bool')
    i.pull_endswith = hive.pull_out(i.endswith)
    ex.endswith = hive.output(i.pull_endswith)

    i.do_find_substr = hive.modifier(do_endswith)

    hive.trigger(i.pull_endswith, i.pull_string, pretrigger=True)
    hive.trigger(i.pull_string, i.pull_substring)
    hive.trigger(i.pull_substring, i.do_find_substr)


EndsWith = hive.hive("EndsWith", build_endswith)