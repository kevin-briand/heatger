"""Led color enum"""
from enum import Enum
from typing import List

from src.shared.enum.state import State


class LedColor(Enum):
    """Led color enum"""
    RED = [True, False, False]
    GREEN = [False, False, True]
    BLUE = [False, True, False]

    @staticmethod
    def data_to_color(data: List[bool]) -> "LedColor":
        """return LedColor corresponding of data given"""
        if data == LedColor.RED.value:
            return LedColor.RED
        if data == LedColor.GREEN.value:
            return LedColor.GREEN
        return LedColor.BLUE

    @staticmethod
    def order_to_color(state: State) -> "LedColor":
        """return LedColor corresponding of Order given"""
        if state == State.COMFORT:
            return LedColor.RED
        if state == State.ECO:
            return LedColor.BLUE
        return LedColor.GREEN
