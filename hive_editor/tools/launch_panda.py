from argparse import ArgumentParser
from contextlib import contextmanager
from os.path import dirname
from os import chdir

from dragonfly.panda3d import Mainloop
from hive_editor.debugging.network import NetworkDebugContext
from hive_editor.code_generator import hivemap_to_python_source
from hive_editor.models import model


parser = ArgumentParser(description="Launch Hivemap in Panda3D")
parser.add_argument('hivemap', type=str)
parser.set_defaults(debug=False)

subparsers = parser.add_subparsers()

parser_debug = subparsers.add_parser('debug')
parser_debug.set_defaults(debug=True)
parser_debug.add_argument('-port', type=int, default=None)
parser_debug.add_argument('-host', type=str, default=None)

args = parser.parse_args()

# Set working directory
directory = dirname(args.hivemap)
chdir(directory)

hive_class_name = "LaunchHive"

# Load hivemap and produce hive
hivemap = model.Hivemap.fromfile(args.hivemap)
source = hivemap_to_python_source(hivemap, hive_class_name)
namespace = {}
exec(source, namespace)
hive_class = namespace[hive_class_name]


# Embed inside Panda mainloop hive
def build_my_hive(i, ex, args):
    i.main_hive = hive_class()


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
