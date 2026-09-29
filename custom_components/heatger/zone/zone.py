"""Zone class"""
from __future__ import annotations

import datetime
import logging
from typing import Callable, Optional

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from ..actuators.base import Actuator
from ..models import Schedule, ZoneConfig, ZonePersist
from ..season import SeasonManager
from ..shared.enum.mode import Mode
from ..shared.enum.season import Season
from ..shared.enum.state import State
from ..shared.listeners import Listeners
from ..shared.timer.timer import Timer
from ..storage import HeatgerStorage
from .base import Base
from .consts import HOME

_LOGGER = logging.getLogger(__name__)


class Zone:
    """A zone computes its state (comfort / eco) and applies it to its actuators.

    - auto mode: the program of the season, a comfort schedule waits for someone at home
    - override: a state until the next schedule or until a date, in auto mode
    - manual mode: the state chosen by the user
    - season stop: no program, eco
    """

    def __init__(self, hass: HomeAssistant, storage: HeatgerStorage, config: ZoneConfig,
                 season: SeasonManager, actuators: list[Actuator], number: int):
        self.hass = hass
        self.storage = storage
        self.config = config
        self.season = season
        self.actuators = actuators
        self.number = number
        self.current_state = State.ECO
        self.is_ping = False
        self.next_change: Optional[datetime.datetime] = None
        self.listeners = Listeners()
        self._slot_timer = Timer(hass)
        self._override_timer = Timer(hass)
        self._untrack: Optional[Callable[[], None]] = None

    # ---- properties

    @property
    def zone_id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def persist(self) -> ZonePersist:
        return self.storage.persist.zone(self.zone_id)

    @property
    def mode(self) -> Mode:
        return self.persist.mode

    @property
    def override_state(self) -> Optional[State]:
        return self.persist.override_state

    @property
    def override_until(self) -> Optional[datetime.datetime]:
        return self.persist.override_until

    def program(self) -> list[Schedule]:
        """program of the current season"""
        key = self.season.current.program
        return self.config.programs.get(key, []) if key else []

    # ---- life cycle

    async def async_start(self) -> None:
        for actuator in self.actuators:
            await actuator.async_start()
        await self.refresh(new_slot=True)

    async def async_stop(self) -> None:
        await self._slot_timer.stop()
        await self._override_timer.stop()
        self._stop_ping()
        for actuator in self.actuators:
            await actuator.async_stop()

    # ---- schedules

    @staticmethod
    def _now_schedule() -> Schedule:
        now = dt_util.now()
        return Schedule(now.weekday(), now.time(), State.ECO)

    @staticmethod
    def find_next_schedule(schedules: list[Schedule], now: Schedule) -> Optional[Schedule]:
        """return the first schedule strictly after now (loop to the beginning of the week)"""
        if not schedules:
            return None
        ordered = sorted(schedules, key=lambda s: s.to_value())
        for schedule in ordered:
            if now.to_value() < schedule.to_value():
                return schedule
        return ordered[0]

    @staticmethod
    def find_current_schedule(schedules: list[Schedule], now: Schedule) -> Optional[Schedule]:
        """return the last schedule started before or at now (loop to the end of the week)"""
        if not schedules:
            return None
        ordered = sorted(schedules, key=lambda s: s.to_value())
        current = ordered[-1]
        for schedule in ordered:
            if schedule.to_value() <= now.to_value():
                current = schedule
        return current

    # ---- state computation

    def _override_active(self) -> bool:
        if self.override_state is None:
            return False
        return self.override_until is None or self.override_until > dt_util.now()

    async def refresh(self, new_slot: bool = False) -> None:
        """compute the state of the zone, start the timers, apply the state to the actuators"""
        await self._slot_timer.stop()
        await self._override_timer.stop()
        self.next_change = None
        season = self.season.current

        if not self._override_active() and self.override_state is not None:
            self._clear_override()

        if season == Season.STOP:
            self._stop_ping()
            state = State.ECO
        elif self.mode == Mode.MANUAL:
            self._stop_ping()
            state = self.persist.state
        else:
            state = await self._auto_state()

        await self._set_state(state, new_slot)

    async def _auto_state(self) -> State:
        schedules = self.program()
        now = self._now_schedule()
        next_schedule = self.find_next_schedule(schedules, now)
        if next_schedule is not None:
            next_date = Base.get_next_day(next_schedule.day, next_schedule.hour)
            await self._slot_timer.start_at(next_date, self._on_slot)
            self.next_change = next_date

        if self._override_active():
            self._stop_ping()
            if self.override_until is not None:
                await self._override_timer.start_at(self.override_until, self._on_override_end)
                if self.next_change is None or self.override_until < self.next_change:
                    self.next_change = self.override_until
            return self.override_state

        current = self.find_current_schedule(schedules, now)
        if current is None:
            # no program: keep the last state
            self._stop_ping()
            return self.persist.state
        if current.state != State.COMFORT:
            self._stop_ping()
            return current.state
        # comfort schedule: comfort only when someone is at home
        if self.persist.state == State.COMFORT or self._someone_home():
            self._stop_ping()
            return State.COMFORT
        self._start_ping()
        return State.ECO

    async def _set_state(self, state: State, new_slot: bool) -> None:
        changed = state != self.current_state
        if changed:
            _LOGGER.info('Zone %s: %s -> %s', self.name, self.current_state.name, state.name)
        self.current_state = state
        if self.season.current != Season.STOP and self.persist.state != state:
            self.persist.state = state
        await self.storage.async_save_persist()
        season = self.season.current
        for actuator in self.actuators:
            await actuator.apply(state, season, new_slot or changed)
        await self.listeners.notify()

    # ---- presence

    def _users(self) -> list[str]:
        return list(self.storage.config.users)

    def _someone_home(self) -> bool:
        users = self._users()
        if not users:
            return True
        for user in users:
            user_state = self.hass.states.get(user)
            if user_state and user_state.state == HOME:
                return True
        return False

    def _start_ping(self) -> None:
        self._stop_ping()
        self.is_ping = True
        self._untrack = async_track_state_change_event(self.hass, self._users(), self._on_user_state)

    def _stop_ping(self) -> None:
        self.is_ping = False
        if self._untrack:
            self._untrack()
            self._untrack = None

    async def _on_user_state(self, event: Event) -> None:
        new_state = event.data.get('new_state')
        if not self.is_ping or new_state is None or new_state.state != HOME:
            return
        _LOGGER.info('Zone %s: %s is at home', self.name, new_state.entity_id)
        self._stop_ping()
        await self._set_state(State.COMFORT, True)

    # ---- timers

    async def _on_slot(self) -> None:
        """a new schedule starts"""
        if self.override_state is not None and self.override_until is None:
            self._clear_override()
        # the presence is checked again for each comfort schedule
        self.persist.state = State.ECO
        await self.refresh(new_slot=True)

    async def _on_override_end(self) -> None:
        self._clear_override()
        await self.refresh(new_slot=True)

    def _clear_override(self) -> None:
        self.persist.override_state = None
        self.persist.override_until = None

    # ---- actions

    async def set_mode(self, mode: Mode) -> None:
        """auto: follow the program, manual: keep the current state"""
        if mode == self.mode:
            return
        self.persist.mode = mode
        self._clear_override()
        if mode == Mode.MANUAL:
            self.persist.state = self.current_state
        _LOGGER.info('Zone %s: mode %s', self.name, mode.name)
        await self.refresh(new_slot=True)

    async def set_manual_state(self, state: State) -> None:
        """manual mode with the given state"""
        self.persist.mode = Mode.MANUAL
        self._clear_override()
        self.persist.state = state
        await self.refresh(new_slot=True)

    async def set_override(self, state: State, until: Optional[datetime.datetime] = None) -> None:
        """auto mode: the state until the date, or until the next schedule if no date.
        manual mode: the manual state is changed"""
        if self.mode == Mode.MANUAL:
            await self.set_manual_state(state)
            return
        if until is not None and until <= dt_util.now():
            return
        self.persist.override_state = state
        self.persist.override_until = until
        await self.refresh(new_slot=True)

    async def clear_override(self) -> None:
        """back to the program"""
        self._clear_override()
        await self.refresh(new_slot=True)

    async def toggle_state(self) -> None:
        """Switch state Comfort <> Eco (until the next schedule in auto mode)"""
        state = State.ECO if self.current_state == State.COMFORT else State.COMFORT
        await self.set_override(state)

    async def toggle_mode(self) -> None:
        await self.set_mode(Mode.MANUAL if self.mode == Mode.AUTO else Mode.AUTO)

    async def on_season_changed(self) -> None:
        """new season: new program, the overrides and the presence are reset"""
        self._clear_override()
        if self.mode == Mode.AUTO:
            self.persist.state = State.ECO
        await self.refresh(new_slot=True)

    # ---- data

    def get_remaining_time(self) -> int:
        if self.next_change is None:
            return -1
        return max(int((self.next_change - dt_util.now()).total_seconds()), 0)

    def get_data(self) -> dict:
        """information for the panel and the card"""
        return {
            'id': self.zone_id,
            'number': self.number,
            'name': self.name,
            'state': self.current_state,
            'mode': self.mode,
            'nextSwitch': self.get_remaining_time(),
            'nextChange': self.next_change.isoformat() if self.next_change else None,
            'isPing': self.is_ping,
            'override': {'state': self.override_state, 'until': self.override_until.isoformat()
                         if self.override_until else None} if self.override_state is not None else None,
            'actuators': [actuator.get_info() for actuator in self.actuators],
        }
