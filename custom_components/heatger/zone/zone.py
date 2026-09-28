"""Zone class"""
import re

from typing import Optional, Dict, Callable

from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

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

    def __init__(self, hass: HomeAssistant, zone_id: str, frostfree_active: bool = False):
        """Initialize class

        :param zone_id: id of the zone in the config (ex: zone1)
        :param frostfree_active: True if the frost-free is currently active
        """
        super().__init__(hass)
        self.zone_id = zone_id
        self.name = ''
        self.current_state = State.ECO
        self.current_mode = Mode.AUTO
        self.next_state = State.ECO
        self.is_ping = False
        self.frostfree_active = frostfree_active
        self.untrack_event: Optional[Callable[[], None]] = None
        self.initialized = False

    async def async_init(self):
        """Initialize state of class"""
        if self.initialized:
            return
        config = await Config(self.hass).get_zone(self.zone_id)
        self.name = config.name
        self.current_mode = Persistence(self.hass).get_mode(self.zone_id)
        await self.__restore_state()
        self.initialized = True

    async def __restore_state(self) -> None:
        """Apply the state matching the current mode (after a reboot, a config change or a mode change)"""
        await self.timer.stop()
        self.__stop_ping()

        if self.frostfree_active:
            await self.set_state(State.FROSTFREE)
            return

        persisted_state = Persistence(self.hass).get_state(self.zone_id)

        if self.current_mode == Mode.MANUAL:
            # manual mode: keep the last state chosen by the user
            await self.set_state(persisted_state)
            return

        # auto mode: apply the state of the current schedule
        current_schedule = await self.get_current_schedule()
        if current_schedule is None:
            await self.set_state(persisted_state)
        elif current_schedule.state == State.COMFORT:
            if persisted_state == State.COMFORT:
                # someone was already detected during this comfort period
                await self.set_state(State.COMFORT)
            else:
                await self.set_state(State.ECO)
                await self.launch_ping()
        else:
            await self.set_state(current_schedule.state)

        await self.start_next_timer()

    async def toggle_mode(self) -> None:
        """Switch mode Auto <> Manual"""
        if self.current_mode == Mode.AUTO:
            self.current_mode = Mode.MANUAL
        else:
            self.current_mode = Mode.AUTO
        await Persistence(self.hass).set_mode(self.zone_id, self.current_mode)
        Logs.info(self.zone_id, "Mode set to " + self.current_mode.name)

        if self.frostfree_active:
            # the new mode will be applied at the end of the frost-free
            return
        if self.current_mode == Mode.MANUAL:
            await self.timer.stop()
            self.__stop_ping()
        else:
            await self.__restore_state()

    async def start_next_timer(self) -> None:
        """Launch next timer (mode Auto)"""
        if self.current_mode != Mode.AUTO or self.frostfree_active:
            return
        next_schedule = await self.get_next_schedule()
        if next_schedule is None:
            return

        next_date = self.get_next_day(next_schedule.day, next_schedule.hour)
        Logs.debug(self.zone_id, F'Selected schedule -> {next_schedule.to_object()}')

        self.next_state = next_schedule.state
        await self.timer.start_at(next_date, self.on_time_out)
        Logs.info(self.zone_id, F'next change ({self.next_state.name}) at {next_date.isoformat()}')

    async def _get_schedules(self) -> list[ScheduleDto]:
        zone_config = await Config(self.hass).get_zone(self.zone_id)
        return zone_config.prog or []

    async def get_next_schedule(self) -> Optional[ScheduleDto]:
        """get the next schedule in prog list"""
        return self.find_next_schedule(await self._get_schedules(), self._now_schedule())

    async def get_current_schedule(self) -> Optional[ScheduleDto]:
        """get the schedule currently applied (the last one started)"""
        return self.find_current_schedule(await self._get_schedules(), self._now_schedule())

    @staticmethod
    def _now_schedule() -> ScheduleDto:
        now = dt_util.now()
        return ScheduleDto(now.weekday(), now.time(), State.ECO)

    @staticmethod
    def find_next_schedule(schedules: list[ScheduleDto], now: ScheduleDto) -> Optional[ScheduleDto]:
        """return the first schedule strictly after now (loop to the beginning of the week)"""
        if not schedules:
            return None
        ordered = sorted(schedules, key=lambda s: s.to_value())
        for schedule in ordered:
            if now.to_value() < schedule.to_value():
                return schedule
        return ordered[0]

    @staticmethod
    def find_current_schedule(schedules: list[ScheduleDto], now: ScheduleDto) -> Optional[ScheduleDto]:
        """return the last schedule started before or at now (loop to the end of the week)"""
        if not schedules:
            return None
        ordered = sorted(schedules, key=lambda s: s.to_value())
        current = ordered[-1]
        for schedule in ordered:
            if schedule.to_value() <= now.to_value():
                current = schedule
        return current

    async def launch_ping(self) -> None:
        """Start users presence check"""
        self.is_ping = True
        await self.ping_users()

    async def ping_users(self) -> None:
        """Users presence check"""
        if not self.is_ping:
            return
        self.__untrack()
        users = (await Config(self.hass).get_config()).users
        if len(users) == 0:
            await self.on_user_home()
            return
        for user in users:
            user_state = self.hass.states.get(user)
            if user_state and user_state.state == HOME:
                await self.on_user_home()
                return
        self.untrack_event = async_track_state_change_event(self.hass, users, self.user_state_change_callback)

    async def user_state_change_callback(self, event: Event) -> None:
        """handle new state of a person entity"""
        new_state = event.data.get('new_state')
        if new_state is not None and new_state.state == HOME:
            self.__untrack()
            await self.on_user_home()

    def __untrack(self) -> None:
        """stop listening the persons states"""
        if self.untrack_event:
            self.untrack_event()
            self.untrack_event = None

    def __stop_ping(self) -> None:
        """stop the presence check"""
        self.is_ping = False
        self.__untrack()

    async def set_state(self, state: State) -> None:
        """change state"""
        if state != self.current_state:
            Logs.info(self.zone_id, F'zone {self.name} switch {self.current_state.name} to {state.name}')
        self.current_state = state
        if state != State.FROSTFREE:
            await Persistence(self.hass).set_state(self.zone_id, state)
        try:
            await WSClient.set_status(self.zone_id, state)
        except Exception as e:  # pylint: disable=broad-except
            # the state is persisted and will be sent again to the server on reconnection
            Logs.error(self.zone_id, F'Failure to send the state to the server: {e}')

    async def on_user_home(self) -> None:
        """Called when a user is at home"""
        if not self.is_ping:
            return
        self.is_ping = False
        await self.set_state(State.COMFORT)

    async def on_time_out(self) -> None:
        """Called when timeout fired"""
        Logs.info(self.zone_id, F'timeout zone {self.name}')
        self.__stop_ping()

        if self.next_state == State.COMFORT:
            await self.launch_ping()
        else:
            await self.set_state(self.next_state)

        await self.start_next_timer()

    async def toggle_state(self) -> None:
        """Switch state Comfort <> Eco"""
        if self.frostfree_active:
            Logs.info(self.zone_id, 'frost-free is active, state not changed')
            return
        self.__stop_ping()
        if self.current_state == State.COMFORT:
            await self.set_state(State.ECO)
        else:
            await self.set_state(State.COMFORT)

    async def set_frostfree(self, activate: bool) -> None:
        """Activate/deactivate frost-free"""
        if self.frostfree_active == activate:
            return
        self.frostfree_active = activate
        await self.__restore_state()

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
        if zone_number is None:
            return -1
        try:
            await Config(hass).get_zone(f'{ZONE}{zone_number.group(0)}')
        except Exception:  # pylint: disable=broad-except
            return -1
        return int(zone_number.group(0))

    async def stop_loop(self):
        """Stop the loop"""
        self.__stop_ping()
        await super().stop_loop()
