

from enum import Enum


class GameMode(Enum):
    FFA = 1
    BALL = 2
    TBD = 3
    TDM = 4
    ONEBD = 5
    ONEDE = 6
    ONEDM = 7

class PyaltEnum(Enum):
    SHUTDOWN = 1
    INOTIFY_ERR = 2

class MapState(Enum):
    INITIALIZED = 1
    LOADING = 2
    READY = 3
    ACTIVE = 4

