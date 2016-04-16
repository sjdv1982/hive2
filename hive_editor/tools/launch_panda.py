from dragonfly.app.panda3d import Mainloop
from argparse import ArgumentParser
from contextlib import contextmanager
from os.path import dirname, basename, splitext

from hive_editor.importer import get_hook
from hive_editor.debugging.network import NetworkDebugContext
from hive_editor.utils import underscore_to_camel_case

parser = ArgumentParser(description="Launch Hivemap in Panda3D")
parser.add_argument('hivemap', type=str)
parser.set_defaults(debug=False)

subparsers = parser.add_subparsers()

parser_debug = subparsers.add_parser('debug')
parser_debug.set_defaults(debug=True)
parser_debug.add_argument('-port', type=int, default=None)
parser_debug.add_argument('-host', type=str, default=None)

args = parser.parse_args()

directory = dirname(args.hivemap)
filename = basename(args.hivemap)
name = splitext(filename)[0]
hive_name = underscore_to_camel_case(name)

import_context = get_hook()
with import_context.temporary_relative_context(directory):
    module = __import__(name, fromlist=[hive_name])
    hivemap_class = getattr(module, hive_name)


def build_my_hive(i, ex, args):
    i.main_hive = hivemap_class()


MainHive = Mainloop.extend("MyHive", build_my_hive)

if args.debug:
    context = NetworkDebugContext(host=args.host, port=args.port)

else:
    @contextmanager
    def context():
        yield

with context:
    main = MainHive()
    main.run()