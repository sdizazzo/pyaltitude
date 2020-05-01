

from enum import Enum

class PyaltEnum(Enum):
    SHUTDOWN = 1
    INOTIFY_ERR = 2

class MapState(Enum):
    INITIALIZED = 1
    LOADING = 2
    READY = 3
    ACTIVE = 4

