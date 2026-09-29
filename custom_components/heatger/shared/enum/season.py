"""Season enum"""
from enum import Enum
from typing import Optional

from custom_components.heatger.const import PROGRAM_WINTER, PROGRAM_SUMMER


class Season(Enum):
    """Global season: decides which program is used and which actuators are controlled"""
    HEATING = 'heating'
    COOLING = 'cooling'
    STOP = 'stop'

    @property
    def program(self) -> Optional[str]:
        """return the program key used during this season, None if no program"""
        if self == Season.HEATING:
            return PROGRAM_WINTER
        if self == Season.COOLING:
            return PROGRAM_SUMMER
        return None
