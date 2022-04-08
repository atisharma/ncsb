"""
An ncurses Squeezebox controller for Logitech Media Server (LMS / slimserver)
"""

import hy
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("package-name")
except PackageNotFoundError:
    # package is not installed
    pass
