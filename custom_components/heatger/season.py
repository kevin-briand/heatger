"""Global season: heating, cooling or stop, optionally until a date"""
from __future__ import annotations

import datetime
import logging
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .models import SeasonPersist
from .shared.enum.season import Season
from .shared.listeners import Listeners
from .shared.timer.timer import Timer
from .storage import HeatgerStorage

_LOGGER = logging.getLogger(__name__)


class SeasonManager:
    """Hold the current season and switch to the next one at the programmed date"""

    def __init__(self, hass: HomeAssistant, storage: HeatgerStorage):
        self.hass = hass
        self.storage = storage
        self.timer = Timer(hass)
        # notified after every change (season, end date or next season)
        self.listeners = Listeners()
        # notified only when the season itself changes, before `listeners`
        self.season_listeners = Listeners()

    @property
    def data(self) -> SeasonPersist:
        return self.storage.persist.season

    @property
    def current(self) -> Season:
        return self.data.current

    @property
    def until(self) -> Optional[datetime.datetime]:
        return self.data.until

    @property
    def next(self) -> Season:
        return self.data.next

    def remaining_seconds(self) -> int:
        """seconds before the end of the programmed season, -1 if not programmed"""
        if self.until is None:
            return -1
        return max(int((self.until - dt_util.now()).total_seconds()), 0)

    async def async_init(self) -> None:
        """apply a programmed end reached while Home Assistant was stopped, start the timer"""
        if self.until is not None and self.until <= dt_util.now():
            _LOGGER.info('Programmed season ended while stopped, switching to %s', self.next.value)
            self.data.current = self.next
            self.data.until = None
            await self.storage.async_save_persist()
        await self._start_timer()

    async def _start_timer(self) -> None:
        await self.timer.stop()
        if self.until is not None:
            await self.timer.start_at(self.until, self._on_end)

    async def _on_end(self) -> None:
        _LOGGER.info('End of the programmed season %s, switching to %s', self.current.value, self.next.value)
        await self.async_set(self.next)

    async def async_set(self, season: Season, until: Optional[datetime.datetime] = None,
                        next_season: Optional[Season] = None) -> None:
        """set the season, optionally until a date, then `next_season` (heating by default)"""
        if until is not None and until <= dt_util.now():
            until = None
        changed = season != self.current
        self.data.current = season
        self.data.until = until
        self.data.next = next_season or Season.HEATING
        await self.storage.async_save_persist()
        await self._start_timer()
        _LOGGER.info('Season set to %s%s', season.value,
                     f' until {dt_util.as_local(until).isoformat()} then {self.data.next.value}' if until else '')
        if changed:
            await self.season_listeners.notify()
        await self.listeners.notify()

    async def async_set_until(self, until: Optional[datetime.datetime],
                              next_season: Optional[Season] = None) -> None:
        """program the end of the current season"""
        await self.async_set(self.current, until, next_season or self.next)

    def get_info(self) -> dict:
        """data for the panel and the card"""
        return {
            'season': self.current.value,
            'until': self.until.isoformat() if self.until else None,
            'next': self.next.value,
            'remaining': self.remaining_seconds(),
        }

    async def async_stop(self) -> None:
        await self.timer.stop()
