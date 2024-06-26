"""Zone class"""
import re

from datetime import datetime
from typing import Optional, Dict

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers.event import async_track_state_change
from homeassistant.core import State as HAState

from custom_components.heatger.websocket.ws_client import WSClient
from custom_components.heatger.local_storage.config.config import Config
from custom_components.heatger.local_storage.persistence.persistence import Persistence
from custom_components.heatger.shared.enum.mode import Mode
from custom_components.heatger.shared.enum.state import State
from custom_components.heatger.shared.logs.logs import Logs
from custom_components.heatger.zone.base import Base
from custom_components.heatger.zone.consts import ZONE, REGEX_FIND_NUMBER, HOME
from custom_components.heatger.zone.dto.schedule_dto import ScheduleDto


class Zone(Base):
    """This class define a new heaters zone"""

    def __init__(self, hass, number: int):
        """Initialize class"""
        super().__init__()
        self.hass: HomeAssistant = hass
        self.zone_id = number.__str__()
        self.name = ''
        self.current_state = State.ECO
        self.current_mode = Mode.AUTO
        self.next_state = State.ECO
        self.is_ping = False
        self.untrack_event = None
        self.initialized = False

    async def async_init(self):
        """Initialize state of class"""
        if self.initialized:
            return
        config = await Config(self.hass).get_zone(F"{ZONE}{self.zone_id}")
        self.zone_id = F"{ZONE}{self.zone_id}"
        self.name = config.name
        await self.__restore_state()
        self.initialized = True

    async def __restore_state(self) -> None:
        """Restore state/mode after a device reboot"""
        self.current_state = Persistence(self.hass).get_state(self.zone_id)

        mode = Persistence(self.hass).get_mode(self.zone_id)
        if self.current_mode != mode:
            await self.toggle_mode()
        else:
            await self.start_next_timer()
        Logs.info('INFO2', 'RESTORE')
        await self.set_state(State.ECO)

        next_schedule = await self.get_next_schedule()
        if next_schedule is not None and next_schedule.state == State.ECO:
            await self.launch_ping()

    async def toggle_mode(self) -> None:
        """Switch mode Auto <> Manual"""
        if self.current_mode == Mode.AUTO:
            self.current_mode = Mode.MANUAL
            await self.timer.stop()
            self.is_ping = False
        else:
            self.current_mode = Mode.AUTO
            await self.start_next_timer()
        await Persistence(self.hass).set_mode(self.zone_id, self.current_mode)
        Logs.info(self.zone_id, "Mode set to " + self.current_mode.name)
        if self.current_mode == Mode.AUTO:
            await self.__restore_state()

    async def start_next_timer(self) -> None:
        """Launch next timer (mode Auto)"""
        if self.current_mode != Mode.AUTO:
            return
        next_schedule = await self.get_next_schedule()
        if next_schedule is None:
            return

        remaining_time = self.get_remaining_time_from_schedule(next_schedule)

        self.next_state = next_schedule.state
        await self.timer.start(remaining_time, self.on_time_out)
        Logs.info(self.zone_id, F'next timeout in {str(remaining_time)}s')

    async def get_next_schedule(self) -> Optional[ScheduleDto]:
        """get the current and next schedule in prog list"""
        zone_config = await Config(self.hass).get_zone(self.zone_id)
        list_schedules = zone_config.prog
        if list_schedules is None or len(list_schedules) == 0:
            return None

        next_schedule: Optional[ScheduleDto] = None
        for schedule in list_schedules:
            schedule_date = Zone.get_next_day(schedule.day, schedule.hour)
            if next_schedule is None or schedule_date < Zone.get_next_day(next_schedule.day, next_schedule.hour):
                next_schedule = schedule
        return next_schedule

    @staticmethod
    def get_remaining_time_from_schedule(schedule: ScheduleDto) -> int:
        """Return the remaining time between the next schedule and now"""
        schedule_date = Zone.get_next_day(schedule.day, schedule.hour)
        Logs.info('TEST', int(schedule_date.timestamp() - datetime.now().timestamp()))
        return int(schedule_date.timestamp() - datetime.now().timestamp())

    async def launch_ping(self) -> None:
        """Start users presence check"""
        self.is_ping = True
        await self.ping_users()

    async def ping_users(self) -> None:
        """Users presence check"""
        if not self.is_ping:
            return
        users = (await Config(self.hass).get_config()).users
        if len(users) == 0:
            await self.on_ip_found()
            return
        for user in users:
            user = self.hass.states.get(user)
            if user and user.state == HOME:
                await self.on_ip_found()
                return
        self.untrack_event = async_track_state_change(self.hass, users, self.user_state_change_callback)

    async def user_state_change_callback(self, entity_id: str, old_state: HAState, new_state: HAState):
        """handle new state of entity"""
        if new_state.state == HOME:
            await self.on_ip_found()
            self.untrack_event()
            self.untrack_event = None

    async def set_state(self, state: State) -> None:
        """change state"""
        Logs.info(self.zone_id, F'zone {self.name} switch {self.current_state.name} to {state.name}')
        self.current_state = state
        if state != State.FROSTFREE:
            await Persistence(self.hass).set_state(self.zone_id, state)
        try:
            await WSClient.set_status(self.zone_id, state)
        except TimeoutError:
            Logs.error(self.zone_id, 'Failure to call service')
        except ServiceNotFound:
            Logs.error(self.zone_id, 'Service not found !')

    async def on_ip_found(self) -> None:
        """Called when ip found on network(Ping class)"""
        if not self.is_ping:
            return
        self.is_ping = False
        await self.set_state(State.COMFORT)

    async def on_time_out(self) -> None:
        """Called when timeout fired"""
        Logs.info(self.zone_id, F'timeout zone {self.name}')
        # stop tracking event
        if self.untrack_event:
            self.untrack_event()
            self.untrack_event = None
        # Wait 5 sec before starting next timer
        await self.timer.start(5, self.start_next_timer)

        if self.next_state == State.COMFORT:
            await self.launch_ping()
        else:
            await self.set_state(self.next_state)
            self.is_ping = False

    async def toggle_state(self) -> None:
        """Switch state Comfort <> Eco"""
        if self.current_state == State.COMFORT:
            await self.set_state(State.ECO)
        else:
            await self.set_state(State.COMFORT)

    async def set_frostfree(self, activate: bool) -> None:
        """Activate/deactivate frost-free"""
        if activate:
            if self.current_mode == Mode.AUTO:
                await self.toggle_mode()
            self.is_ping = False
            await self.set_state(State.FROSTFREE)
        elif self.current_mode == Mode.MANUAL:
            await self.toggle_mode()

    def get_data(self) -> Dict:
        """return information zone in json object"""
        return {
            'name': self.name,
            'state': self.current_state,
            'mode': self.current_mode,
            'nextSwitch': self.get_remaining_time(),
            'isPing': self.is_ping
        }

    @staticmethod
    async def get_zone_number(hass: HomeAssistant, topic: str) -> int:
        """Return the zone number, else -1"""
        zone_number = re.search(REGEX_FIND_NUMBER, topic)
        if zone_number is None or not hasattr(await Config(hass).get_config(), f'{ZONE}{zone_number.group(0)}'):
            return -1
        return int(zone_number.group(0))

    async def stop_loop(self):
        """Stop the loop"""
        self.is_ping = False
        await super().stop_loop()
