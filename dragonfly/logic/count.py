import hive


def do_count(self):
    self.count += 1


def build_count(i, ex, args):
    """Simple integer counter"""
    args.start_value = hive.parameter("int", 0)
    ex.count = hive.attribute("int", args.start_value)

    i.modifier = hive.modifier(do_count)
    ex.do_increment = hive.entry(i.modifier)

    i.count_out = hive.pull_out(ex.count)
    ex.count_out = hive.output(i.count_out)


Count = hive.hive("Count", build_count)
