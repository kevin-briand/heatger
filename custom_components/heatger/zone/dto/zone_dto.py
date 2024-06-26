"""object for config file"""
import datetime
from dataclasses import dataclass
from typing import List

from custom_components.heatger.shared.enum.state import State
from custom_components.heatger.zone.dto.schedule_dto import ScheduleDto


@dataclass
class ZoneDto:
    """zone data object"""

    def __init__(self, name: str, enabled: bool, prog: [], **kwargs):
        self.name = name
        self.enabled = enabled
        schedules = []
        if self.is_list_of_schedule_dto(prog):
            schedules = prog
        else:
            for schedule in prog:
                hour = int(schedule['hour'].split(':')[0])
                minute = int(schedule['hour'].split(':')[1])
                schedules.append(ScheduleDto(schedule['day'], datetime.time(hour, minute),
                                             State.to_state(int(schedule['state']))))
        self.prog = schedules

    @staticmethod
    def is_list_of_schedule_dto(obj: list) -> bool:
        """return true if the given list is a list of ScheduleDto"""
        return isinstance(obj, List) and all(isinstance(item, ScheduleDto) for item in obj)

    def to_object(self):
        """"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'prog': [prog.to_object() for prog in self.prog]
        }
