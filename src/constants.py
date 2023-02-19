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


class Operation(Enum):
    SELECT_LEFTHAND = 0
    SELECT_RIGHTHAND = 1
    PAN_LEFTHAND = 2
    PAN_RIGHTHAND = 3
    ZOOM = 4
    IDLE = 99


class OperationTransition(Enum):
    SELECTLEFT_TO_SELECTRIGHT = 0
    SELECTLEFT_TO_PANLEFT = 1
    SELECTLEFT_TO_PANRIGHT = 2
    SELECTLEFT_TO_ZOOM = 3
    SELECTLEFT_TO_IDLE = 4
    SELECTRIGHT_TO_SELECTLEFT = 5
    SELECTRIGHT_TO_PANLEFT = 6
    SELECTRIGHT_TO_PANRIGHT = 7
    SELECTRIGHT_TO_ZOOM = 8
    SELECTRIGHT_TO_IDLE = 9
    PANLEFT_TO_SELECTLEFT = 10
    PANLEFT_TO_SELECTRIGHT = 11
    PANLEFT_TO_PANRIGHT = 12
    PANLEFT_TO_ZOOM = 13
    PANLEFT_TO_IDLE = 14
    PANRIGHT_TO_SELECTLEFT = 15
    PANRIGHT_TO_SELECTRIGHT = 16
    PANRIGHT_TO_PANLEFT = 17
    PANRIGHT_TO_ZOOM = 18
    PANRIGHT_TO_IDLE = 19
    ZOOM_TO_SELECTLEFT = 20
    ZOOM_TO_SELECTRIGHT = 21
    ZOOM_TO_PANLEFT = 22
    ZOOM_TO_PANRIGHT = 23
    ZOOM_TO_IDLE = 24
    IDLE_TO_SELECTLEFT = 25
    IDLE_TO_SELECTRIGHT = 26
    IDLE_TO_PANLEFT = 27
    IDLE_TO_PANRIGHT = 28
    IDLE_TO_ZOOM = 29
    REMAINS = 99  # Used when the operation remains the same
