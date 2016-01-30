from struct import pack

from hive.debug import RemoteDebugContext, pack_pascal_string, OpCodes
from ..importer import get_hook


class HivemapDebugContext(RemoteDebugContext):

    def _find_root_hive(self, bee):
        # Find path to actual root
        root_path_reverse = []
        while getattr(bee, 'parent', None):
            bee = bee.parent
            root_path_reverse.append(bee)

        # Now find first hivemap
        importer = get_hook()
        get_file_path = importer.get_path_of_class
        for parent in reversed(root_path_reverse):
            try:
                parent_builder_class = parent._hive_object._hive_parent_class

            except AttributeError:
                raise ValueError("This bee is never created by a hivemap-hive")

            # If this fails, not a hivemap hive
            try:
                get_file_path(parent_builder_class)
            except ValueError:
                pass

            else:
                return parent

    def _notify_create_root_hive(self, root_hive, root_hive_id):
        importer = get_hook()
        hive_parent_class = root_hive._hive_object._hive_parent_class
        file_path = importer.get_path_of_class(hive_parent_class)

        data = pack_pascal_string(file_path) + pack('B', root_hive_id)
        self._send_command(OpCodes.register_root, data)
