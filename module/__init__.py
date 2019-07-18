"""

MODULE PACKAGE
---

An extension for simple, user-created modules.

Place any custom modules in the package folder and they will be imported automatically.
"""

# todo:
#   setup low level async logic for accessing databases and other servers, import.
#   figure out what else is necessary here.

from .base import Module, Command
from .fun import *
from .nsfw import *
from .steam import *
from .stattrack import *
from .player import *
from .image import *
from .fishing import *
from .telephone import *
