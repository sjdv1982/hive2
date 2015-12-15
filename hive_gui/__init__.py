from hive import set_validation_enabled
from .importer import install_hook, uninstall_hook, get_hook

install_hook()

# Disable connectivity validation
set_validation_enabled(False)
