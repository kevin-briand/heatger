"""Orders enum"""
from enum import Enum


class State(Enum):
    """Orders enum"""
    COMFORT = 0
    ECO = 1
    FROSTFREE = 2

    @staticmethod
    def to_state(state_num: int):
        """return Order corresponding of number given"""
        if state_num == State.COMFORT.value:
            return State.COMFORT
        if state_num == State.ECO.value:
            return State.ECO
        return State.FROSTFREE
