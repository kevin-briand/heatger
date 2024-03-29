"""Test zone class"""
import time
import unittest
from datetime import datetime
from threading import Thread
from typing import Optional

from src.localStorage.config.config import Config
from src.localStorage.persistence.persistence import Persistence
from src.shared.enum.mode import Mode
from src.shared.enum.state import State
from src.zone.dto.info_zone import InfoZone
from src.zone.dto.schedule_dto import ScheduleDto
from src.zone.zone import Zone
from test.helpers.fixtures.zone.schedule_dto_fixture import schedule_dto_fixture
from test.helpers.patchs.config_patch import ConfigPatch
from test.helpers.patchs.persistence_patch import PersistencePatch
from test.helpers.patchs.zone_patch import ZonePatch

ZONE1 = "zone1"


class TestZone(unittest.TestCase):

    def setUp(self):
        PersistencePatch.start_patch(self)
        ConfigPatch.start_patch(self)
        ZonePatch.start_patch(self)

        self.thread = None
        self.zone: Optional[Zone] = None

    def tearDown(self) -> None:
        if self.zone:
            self.zone.stop_loop()
        self.zone = None

        ZonePatch.stop_patch(self)
        PersistencePatch.stop_patch(self)
        ConfigPatch.stop_patch(self)

    @staticmethod
    def ip_scan(ip: str):
        time.sleep(1)
        return [ip]

    def start_thread(self):
        self.thread = Thread(target=self.run_zone())
        self.thread.start()
        time.sleep(0.5)

    def run_zone(self):
        self.zone = Zone(1)

    def test_create_zone(self):
        Config().add_schedules(ZONE1, [schedule_dto_fixture(), schedule_dto_fixture()])

        self.start_thread()

        self.assertGreater(self.zone.get_remaining_time(), 0)

    def test_restore_mode_on_startup(self):
        Persistence().set_mode(ZONE1, Mode.MANUAL)

        self.start_thread()

        self.assertEqual(self.zone.get_remaining_time(), -1)
        self.assertEqual(self.zone.current_mode, Mode.MANUAL)

    def test_restore_state_on_startup(self):
        Persistence().set_state(ZONE1, State.COMFORT)
        now = datetime.now()
        next_hour = now.time().replace(hour=now.hour + 1)
        Config().add_schedule(ZONE1, ScheduleDto(now.weekday(), next_hour, State.ECO))

        self.start_thread()

        self.assertEqual(self.zone.current_state, State.COMFORT)

    def test_toggle_mode(self):
        Config().add_schedules(ZONE1, [schedule_dto_fixture(), schedule_dto_fixture()])

        self.start_thread()
        self.assertEqual(self.zone.current_mode, Mode.AUTO)
        self.assertGreater(self.zone.get_remaining_time(), 0)

        self.zone.toggle_mode()
        self.assertEqual(self.zone.current_mode, Mode.MANUAL)
        self.assertEqual(self.zone.get_remaining_time(), -1)

        self.zone.toggle_mode()
        time.sleep(0.5)
        self.assertEqual(self.zone.current_mode, Mode.AUTO)
        self.assertGreater(self.zone.get_remaining_time(), 0)

    def test_start_next_state_should_return_if_mode_is_not_auto(self):
        Persistence().set_mode(ZONE1, Mode.MANUAL)

        self.start_thread()
        self.zone.start_next_timer()

        self.assertEqual(self.zone.get_remaining_time(), -1)

    def test_start_next_state_should_return_if_schedule_is_none(self):
        self.start_thread()
        self.zone.start_next_timer()

        self.assertEqual(self.zone.get_remaining_time(), -1)

    def test_get_next_schedule(self):
        now = datetime.now()
        past_hour = now.time().replace(hour=now.hour - 1)
        next_hour = now.time().replace(hour=now.hour + 1)
        past_schedule = ScheduleDto(now.weekday(), past_hour, State.COMFORT)
        next_schedule = ScheduleDto(now.weekday(), next_hour, State.ECO)
        Config().add_schedules(ZONE1, [past_schedule, next_schedule])

        self.start_thread()
        next_result = self.zone.get_next_schedule()

        self.assertEqual(next_result, next_schedule)

    def test_on_ip_found_should_not_change_state_if_not_is_ping(self):
        Config().add_schedule(ZONE1, schedule_dto_fixture(State.COMFORT))

        self.start_thread()
        self.zone.is_ping = False
        self.zone.on_ip_found()

        self.assertEqual(self.zone.current_state, State.ECO)

    def test_on_time_out_switch_to_comfort(self):
        Config().add_schedule(ZONE1, schedule_dto_fixture(State.COMFORT))

        self.start_thread()
        self.zone.on_time_out()
        time.sleep(0.5)

        self.assertEqual(self.zone.current_state, State.COMFORT)

    def test_on_time_out_switch_to_eco(self):
        Config().add_schedule(ZONE1, schedule_dto_fixture(State.ECO))

        self.start_thread()
        self.zone.on_time_out()

        self.assertEqual(self.zone.current_state, State.ECO)

    def test_toggle_state(self):
        Config().add_schedule(ZONE1, schedule_dto_fixture(State.ECO))

        self.start_thread()
        self.assertEqual(self.zone.current_state, State.COMFORT)

        self.zone.toggle_state()
        self.assertEqual(self.zone.current_state, State.ECO)

        self.zone.toggle_state()
        self.assertEqual(self.zone.current_state, State.COMFORT)

    def test_activate_frostfree(self):
        Config().add_schedule(ZONE1, schedule_dto_fixture(State.COMFORT))

        self.start_thread()
        self.zone.set_frostfree(True)

        self.assertEqual(self.zone.current_mode, Mode.MANUAL)
        self.assertEqual(self.zone.current_state, State.FROSTFREE)

        self.zone.set_frostfree(False)

        self.assertEqual(self.zone.current_mode, Mode.AUTO)
        self.assertEqual(self.zone.current_state, State.ECO)

    def test_get_data(self):
        now = datetime.now()
        end_date = now.replace(second=0, microsecond=0)
        schedule = ScheduleDto(now.weekday(), end_date.time(), State.COMFORT)
        Config().add_schedule(ZONE1, schedule)

        self.start_thread()
        target_data = InfoZone(self.zone.zone_id, self.zone.name,
                               self.zone.current_state, end_date, False, self.zone.current_mode)
        data = self.zone.get_data()

        self.assertEqual(data, target_data)
        self.assertNotEqual(data.next_change, None)

        self.zone.toggle_mode()
        data = self.zone.get_data()
        self.assertEqual(data.next_change, None)

    def test_get_zone_number(self):
        result = Zone.get_zone_number("zone1")

        self.assertEqual(result, 1)

    def test_get_zone_number_should_return_error_if_not_found_number(self):
        result = Zone.get_zone_number("zoneX")

        self.assertEqual(result, -1)


if __name__ == '__main__':
    unittest.main()
