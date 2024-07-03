"""object for config file"""
import datetime
from dataclasses import dataclass
from datetime import time

from custom_components.heatger.shared.enum.state import State


@dataclass
class ScheduleDto:
    """schedule data object"""

    # pylint: disable=unused-argument
    def __init__(self, day, hour: time, state, **kwargs):
        self.day = day
        self.hour = hour
        self.state = state

    def __eq__(self, other: 'ScheduleDto'):
        if other is None:
            return False
        return self.to_value() == other.to_value()

    def is_valid_schedule(self) -> bool:
        """return True schedule is valid"""
        return 0 <= self.day <= 6 and isinstance(self.hour, time) and isinstance(self.state, State)

    def to_value(self) -> int:
        """return a schedule in value, the bigger it is, the closer it is to the weekend"""
        return self.day * 10000 + self.hour.hour * 100 + self.hour.minute

    def to_object(self) -> {}:
        """return schedule into object"""
        return {'day': self.day,
                'hour': self.hour,
                'state': self.state.value}

    @staticmethod
    def from_array(data: list) -> list['ScheduleDto']:
        """convert json array to array of scheduleDto"""
        list_horaire = []
        for horaire in data:
            list_horaire.append(ScheduleDto.from_dict(horaire))
        return list_horaire

    @staticmethod
    def from_dict(data: dict):
        hour = int(data['hour'].split(':')[0])
        minute = int(data['hour'].split(':')[1])
        return ScheduleDto(int(data['day']), datetime.time(hour, minute), State.to_state(data['state']))
