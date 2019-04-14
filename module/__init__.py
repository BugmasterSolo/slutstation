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

# programatically import all modules placed in a subfolder.
# this will provide access to the rest of them.
# :)

module_list = os.listdir()
for str in module_list:
    # pop off the .py if it is present, better way to do this
    if str[-3:] == ".py":
        # assume it is a valid module file
        importlib.import_module(str[:-3], ".")
