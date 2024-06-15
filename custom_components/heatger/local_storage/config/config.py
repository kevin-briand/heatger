"""Config class"""
from typing import Optional

from custom_components.heatger.local_storage.config.dto.config_dto import ConfigDto
from custom_components.heatger.local_storage.config.errors.already_exist_error import AlreadyExistError
from custom_components.heatger.local_storage.config.errors.config_error import ConfigError
from custom_components.heatger.local_storage.config.errors.schedule_not_valid_error import ScheduleNotValidError
from custom_components.heatger.local_storage.config.errors.zone_not_found_error import ZoneNotFoundError
from custom_components.heatger.local_storage.errors.missing_arg_error import MissingArgError
from custom_components.heatger.local_storage.local_storage import LocalStorage
from custom_components.heatger.zone.dto.schedule_dto import ScheduleDto
from custom_components.heatger.zone.dto.zone_dto import ZoneDto


class Config(LocalStorage):
    """Class for reading/writing the configuration in file"""
    _initialized = False
    _instance: Optional['Config'] = None

    def __new__(cls, *args, **kwargs) -> 'Config':
        if not isinstance(cls._instance, cls):
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self, hass):
        if Config._initialized:
            return
        super().__init__(hass, 'config')
        self.data: Optional[ConfigDto] = None
        Config._initialized = True

    async def get_config(self) -> ConfigDto:
        """Return a ConfigDto object"""
        if self.data:
            return self.data
        try:
            data = await self._read()
            if not data:
                self.data = ConfigDto({}, [])
            else:
                self.data = ConfigDto(**data)
        except TypeError as exc:
            raise MissingArgError() from exc
        return self.data

    async def __save_data(self, config) -> None:
        """Write a ConfigDto object to file"""
        self.data = config
        await self._write(config)

    async def add_user(self, user) -> None:
        """Add user to scanned users list"""
        if user == '':
            return
        config = await self.get_config()
        users = config.users
        users_list = users
        if not all(user_in_list != user for user_in_list in users_list):
            raise AlreadyExistError(user.ip)

        users_list.append(user)
        await self.__save_data(config)

    async def remove_user(self, user) -> None:
        """Remove user from scanned users list"""
        config = await self.get_config()
        users = config.users
        users.remove(user)
        await self.__save_data(config)

    async def add_schedule(self, zone_id: str, schedule: ScheduleDto) -> None:
        """Add schedule to prog list"""
        if not schedule.is_valid_schedule():
            raise ScheduleNotValidError()
        if not await self.__is_zone_exist(zone_id):
            raise ZoneNotFoundError(zone_id)

        config = await self.get_config()
        zone = config.zones[zone_id]
        prog: list[ScheduleDto] = zone.prog

        if not all(sch.to_value() != schedule.to_value() for sch in prog):
            raise AlreadyExistError('Schedule')
        prog.append(schedule)
        prog.sort(key=Config._sort_schedule)
        await self.__save_data(config)

    async def add_schedules(self, zone_id: str, schedules: [ScheduleDto]) -> None:
        """Add schedules list to prog list"""
        if not await self.__is_zone_exist(zone_id):
            raise ZoneNotFoundError(zone_id)
        for schedule in schedules:
            try:
                await self.add_schedule(zone_id, schedule)
            except ConfigError:
                pass

    @staticmethod
    def _sort_schedule(schedule: ScheduleDto) -> int:
        """Return schedule to a value"""
        return ScheduleDto(schedule.day, schedule.hour, schedule.state).to_value()

    async def remove_schedule(self, zone_id: str, schedule: ScheduleDto) -> None:
        """Remove schedule from prog list"""
        if not schedule.is_valid_schedule():
            raise ScheduleNotValidError()
        if not await self.__is_zone_exist(zone_id):
            raise ZoneNotFoundError(zone_id)

        config = await self.get_config()
        zone = config.zones[zone_id]
        prog = zone.prog
        prog.remove(schedule)
        await self.__save_data(config)

    async def remove_all_schedule(self, zone_id: str) -> None:
        """Remove all schedules from prog list"""
        if not await self.__is_zone_exist(zone_id):
            raise ZoneNotFoundError(zone_id)
        config = await self.get_config()
        zone = config.zones[zone_id]
        prog = zone.prog
        prog.clear()
        zone.prog = prog

        setattr(await self.get_config(), zone_id, zone)
        await self.__save_data(config)

    async def add_zone(self, name: str) -> None:
        """"""
        if name == '':
            return
        config = await self.get_config()
        for [key, zone] in config.zones.items():
            if zone.name == name:
                return

        config.zones[F'zone{len(config.zones.items())+1}'] = ZoneDto(name, True, [])

        await self.__save_data(config)

    async def remove_zone(self, name: str) -> None:
        """"""
        if name == '':
            return
        config = await self.get_config()
        zone_id = ''
        config.zones.items()
        for [key, zone] in config.zones.items():
            if zone.name == name:
                zone_id = key
        config.zones.pop(zone_id)
        await self.__save_data(config)
        self.data = None

    async def __is_zone_exist(self, zone_id: str) -> bool:
        """Return True if the zone exists in the config file"""
        if zone_id is None:
            return False
        try:
            (await self.get_config()).zones[zone_id]
        except KeyError:
            return False
        return True

    async def get_zone(self, zone_id: str) -> ZoneDto:
        """Return the ZoneDto corresponding to the zone_id"""
        if not await self.__is_zone_exist(zone_id):
            raise ZoneNotFoundError(zone_id)
        return (await self.get_config()).zones[zone_id]

    def get_ws_url(self):
        """return the url of ws server"""
        return self.data.ws_url if self.data and hasattr(self.data, 'ws_url') else None

    async def set_ws_url(self, ip):
        """set the url of ws server"""
        config = self.data
        config.ws_url = F'http://{ip}'
        await self.__save_data(config)
