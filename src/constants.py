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
    POINTING = 5
    IDLE = 99


class OperationTransition(Enum):
    SELECT_TO_PANLEFT = 0
    SELECT_TO_PANRIGHT = 1
    SELECT_TO_ZOOM = 2
    SELECT_TO_POINTING = 3
    SELECT_TO_IDLE = 4
    PANLEFT_TO_SELECT = 5
    PANLEFT_TO_PANRIGHT = 6
    PANLEFT_TO_ZOOM = 7
    PANLEFT_TO_POINTING = 8
    PANLEFT_TO_IDLE = 9
    PANRIGHT_TO_SELECT = 10
    PANRIGHT_TO_PANLEFT = 11
    PANRIGHT_TO_ZOOM = 12
    PANRIGHT_TO_POINTING = 13
    PANRIGHT_TO_IDLE = 14
    ZOOM_TO_SELECT = 15
    ZOOM_TO_PANLEFT = 16
    ZOOM_TO_PANRIGHT = 17
    ZOOM_TO_POINTING = 18
    ZOOM_TO_IDLE = 19
    POINTING_TO_SELECT = 20
    POINTING_TO_PANLEFT = 21
    POINTING_TO_PANRIGHT = 22
    POINTING_TO_ZOOM = 23
    POINTING_TO_IDLE = 24
    IDLE_TO_SELECT = 25
    IDLE_TO_PANLEFT = 26
    IDLE_TO_PANRIGHT = 27
    IDLE_TO_ZOOM = 28
    IDLE_TO_POINTING = 29
    REMAINS = 99  # Used when the operation remains the same
