from enum import Enum


class HandState(Enum):
    OPEN = 0
    CLOSED = 1
    POINTER = 2
    UNTRACKED = 3


class Handednes(Enum):
    LEFT = 0
    RIGHT = 1
