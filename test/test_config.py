import unittest
from unittest.mock import mock_open, patch

from src.localStorage.config.config import Config
from src.localStorage.config.errors.already_exist_error import AlreadyExistError
from src.localStorage.config.errors.bad_ip_format_error import BadIpFormatError
from src.localStorage.config.errors.config_error import ConfigError
from src.localStorage.config.errors.schedule_not_valid_error import ScheduleNotValidError
from src.localStorage.config.errors.zone_not_found_error import ZoneNotFoundError
from src.localStorage.errors.missing_arg_error import MissingArgError
from test.helpers.fixtures.localStorage.config.config_dto_fixture import config_dto_fixture
from test.helpers.fixtures.localStorage.config.ip_dto_fixture import ip_dto_fixture
from test.helpers.fixtures.zone.schedule_dto_fixture import schedule_dto_fixture
from test.helpers.patchs.config_patch import ConfigPatch

ZONE_ID = "zone1"
BAD_ZONE_ID = "zone3"


class TestConfig(unittest.TestCase):
    config_datas: str = None

    def setUp(self) -> None:
        self.config = config_dto_fixture()
        ConfigPatch.start_patch(self)

    def tearDown(self) -> None:
        ConfigPatch.stop_patch(self)

    def test_throw_args_error_in_get_config(self):
        Config._initialized = False
        broken_config = self.config
        broken_config.__delattr__('mqtt')
        mock_open_obj = mock_open()
        mock_open_obj.return_value.read.return_value = broken_config

        with patch('src.localStorage.local_storage.open', mock_open_obj):
            with self.assertRaises(MissingArgError):
                Config().get_config()

    def test_add_ip(self):
        new_ip = ip_dto_fixture()

        Config().add_ip(new_ip)
        result = Config().get_config().network.ip

        self.assertIn(new_ip, result)

    def test_throw_bad_ip_format_error_in_add_ip(self):
        bad_ip_format = ip_dto_fixture()
        bad_ip_format.ip = 'badFormat'

        with self.assertRaises(ConfigError):
            Config().add_ip(bad_ip_format)

    def test_throw_exist_ip_error_in_add_ip(self):
        ip = ip_dto_fixture()
        Config().add_ip(ip)
        self.assertEqual(Config().get_config().network.ip, [ip])

        with self.assertRaises(AlreadyExistError):
            Config().add_ip(ip)

    def test_remove_ip(self):
        ip = ip_dto_fixture()
        Config().add_ip(ip)
        self.assertEqual(Config().get_config().network.ip, [ip])

        Config().remove_ip(ip)
        result = Config().get_config().network.ip

        self.assertNotIn(ip, result)

    def test_throw_bad_ip_format_error_in_remove_ip(self):
        bad_ip_format = ip_dto_fixture()
        bad_ip_format.ip = 'badFormat'

        with self.assertRaises(BadIpFormatError):
            Config().remove_ip(bad_ip_format)

    def test_add_schedule(self):
        new_schedule = schedule_dto_fixture()

        Config().add_schedule(ZONE_ID, new_schedule)
        result = Config().get_config().zone1.prog

        self.assertIn(new_schedule, result)

    def test_throw_bad_schedule_error_in_add_schedule(self):
        bad_schedule = schedule_dto_fixture()
        bad_schedule.day = 8

        with self.assertRaises(ScheduleNotValidError):
            Config().add_schedule(ZONE_ID, bad_schedule)

    def test_throw_zone_not_found_error_in_add_schedule(self):
        bad_schedule = schedule_dto_fixture()

        with self.assertRaises(ZoneNotFoundError):
            Config().add_schedule(BAD_ZONE_ID, bad_schedule)

    def test_throw_already_exist_error_in_add_schedule(self):
        schedule = schedule_dto_fixture()
        Config().add_schedule(ZONE_ID, schedule)
        self.assertEqual(Config().get_config().zone1.prog, [schedule])

        with self.assertRaises(AlreadyExistError):
            Config().add_schedule(ZONE_ID, schedule)

    def test_add_schedules(self):
        new_schedules = [schedule_dto_fixture(), schedule_dto_fixture()]

        Config().add_schedules(ZONE_ID, new_schedules)
        result = Config().get_config().zone1.prog
        original = self.config.zone1.prog + new_schedules
        original.sort(key=Config._sort_schedule)

        self.assertEqual(result, original)

    def test_throw_zone_not_found_error_in_add_schedules(self):
        bad_schedule = schedule_dto_fixture()

        with self.assertRaises(ZoneNotFoundError):
            Config().add_schedules(BAD_ZONE_ID, [bad_schedule])

    def test_should_pass_if_schedule_already_exist_in_add_schedules(self):
        schedules = [schedule_dto_fixture(), schedule_dto_fixture()]
        Config().add_schedule(ZONE_ID, schedules[0])
        self.assertEqual(Config().get_config().zone1.prog, [schedules[0]])

        Config().add_schedules(ZONE_ID, schedules)

        schedules.sort(key=Config._sort_schedule)
        result = Config().get_config().zone1.prog
        self.assertEqual(schedules, result)

    def test_remove_schedule(self):
        schedule = schedule_dto_fixture()
        Config().add_schedule(ZONE_ID, schedule)
        self.assertEqual(Config().get_config().zone1.prog, [schedule])

        Config().remove_schedule(ZONE_ID, schedule)
        result = Config().get_config().zone1.prog

        self.assertEqual(result, [])

    def test_throw_bad_schedule_error_in_remove_schedule(self):
        bad_schedule = schedule_dto_fixture()
        bad_schedule.day = 8

        with self.assertRaises(ScheduleNotValidError):
            Config().remove_schedule(ZONE_ID, bad_schedule)

    def test_throw_zone_not_found_error_in_remove_schedule(self):
        bad_schedule = schedule_dto_fixture()

        with self.assertRaises(ZoneNotFoundError):
            Config().remove_schedule(BAD_ZONE_ID, bad_schedule)

    def test_remove_all_schedules(self):
        Config().remove_all_schedule(ZONE_ID)
        result = Config().get_config().zone1.prog
        original = []

        self.assertEqual(result, original)

    def test_throw_zone_not_found_error_in_remove_all_schedule(self):
        with self.assertRaises(ZoneNotFoundError):
            Config().remove_all_schedule(None)

    def test_get_zone(self):
        result = Config().get_zone(ZONE_ID)
        original = self.config.zone1

        self.assertEqual(result, original)

    def test_throw_zone_not_found_error_in_get_zone(self):
        with self.assertRaises(ZoneNotFoundError):
            Config().get_zone(BAD_ZONE_ID)


if __name__ == '__main__':
    unittest.main()
