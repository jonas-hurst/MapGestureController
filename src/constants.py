from __future__ import annotations
from enum import Enum
from numbers import Real


class HandState(Enum):
    OPEN = 0
    CLOSED = 1
    POINTER = 2
    UNTRACKED = 3

    @staticmethod
    def from_classification_result(result: Real) -> HandState:
        if result == 0:
            return HandState.OPEN
        if result == 1:
            return HandState.CLOSED
        if result == 2:
            return HandState.POINTER
        return HandState.UNTRACKED



class Handednes(Enum):
    LEFT = 0
    RIGHT = 1
    INVALID = 2
