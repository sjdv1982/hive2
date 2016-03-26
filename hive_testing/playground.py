import hive_editor
from tcp_test import TcpTest
from dragonfly.app.panda3d import Mainloop
from dragonfly.event import EventManager

import hive


def build(i, ex, args):
    i.h = TcpTest()


H = Mainloop.extend("H", build)
h = H()
h.run()
