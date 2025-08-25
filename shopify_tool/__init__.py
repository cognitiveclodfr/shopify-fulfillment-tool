from .logger_config import setup_logging

# Ensure logging is configured as soon as the package is imported
setup_logging()

# Explicitly import submodules to build the package namespace.
# This helps PyInstaller correctly identify dependencies and avoids import errors.
# The order can be important to prevent circular dependencies.
from . import analysis
from . import packing_lists
from . import stock_export
from . import rules
from . import core
