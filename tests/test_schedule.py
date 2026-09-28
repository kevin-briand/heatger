"""Test the schedule computations."""
import datetime
from zoneinfo import ZoneInfo

from custom_components.heatger.shared.enum.state import State
from custom_components.heatger.zone.base import Base
from custom_components.heatger.zone.dto.schedule_dto import ScheduleDto
from custom_components.heatger.zone.zone import Zone

PARIS = ZoneInfo('Europe/Paris')


def paris(*args) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=PARIS)


def test_next_day_same_week():
    now = paris(2026, 9, 28, 12, 0)  # monday
    assert Base.get_next_day(2, datetime.time(7, 30), now) == paris(2026, 9, 30, 7, 30)


def test_next_day_now_or_passed_is_next_week():
    now = paris(2026, 9, 28, 12, 0)  # monday
    assert Base.get_next_day(0, datetime.time(12, 0), now) == paris(2026, 10, 5, 12, 0)
    assert Base.get_next_day(0, datetime.time(11, 59), now) == paris(2026, 10, 5, 11, 59)
    assert Base.get_next_day(0, datetime.time(12, 1), now) == paris(2026, 9, 28, 12, 1)


def test_next_day_across_dst_change():
    now = paris(2026, 10, 24, 12, 0)  # saturday, summer time (UTC+2)
    result = Base.get_next_day(6, datetime.time(7, 0), now)
    assert result == paris(2026, 10, 25, 7, 0)
    assert result.utcoffset() == datetime.timedelta(hours=1)  # winter time


SCHEDULES = [
    ScheduleDto(0, datetime.time(7, 0), State.COMFORT),
    ScheduleDto(0, datetime.time(22, 0), State.ECO),
    ScheduleDto(4, datetime.time(7, 0), State.COMFORT),
    ScheduleDto(4, datetime.time(22, 0), State.ECO),
]


def test_find_next_schedule():
    now = ScheduleDto(0, datetime.time(12, 0), State.ECO)
    assert Zone.find_next_schedule(SCHEDULES, now) == SCHEDULES[1]
    # after the last schedule of the week: loop to the first one
    now = ScheduleDto(6, datetime.time(12, 0), State.ECO)
    assert Zone.find_next_schedule(SCHEDULES, now) == SCHEDULES[0]
    assert Zone.find_next_schedule([], now) is None


def test_find_current_schedule():
    now = ScheduleDto(0, datetime.time(12, 0), State.ECO)
    assert Zone.find_current_schedule(SCHEDULES, now) == SCHEDULES[0]
    # exactly at the schedule time
    now = ScheduleDto(4, datetime.time(22, 0), State.ECO)
    assert Zone.find_current_schedule(SCHEDULES, now) == SCHEDULES[3]
    # before the first schedule of the week: the last one of previous week applies
    now = ScheduleDto(0, datetime.time(6, 0), State.ECO)
    assert Zone.find_current_schedule(SCHEDULES, now) == SCHEDULES[3]
    assert Zone.find_current_schedule([], now) is None
