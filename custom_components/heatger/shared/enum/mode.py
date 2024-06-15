"""Mode enum"""
from enum import Enum


class Mode(Enum):
    """Mode enum"""
    AUTO = 0
    MANUAL = 1

    @staticmethod
    def to_mode(mode_num: int):
        """return Mode corresponding of number given"""
        if mode_num == Mode.AUTO.value:
            return Mode.AUTO
        return Mode.MANUAL
