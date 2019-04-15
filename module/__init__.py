"""

MODULE PACKAGE
---

An extension for simple, user-created modules.

Place any custom modules in the package folder and they will be imported automatically.
"""

# todo:
#   setup low level async logic for accessing databases and other servers, import.
#   figure out what else is necessary here.

import importlib
import os

from .base import Module, Command
from .fun import *
from .nsfw import *
