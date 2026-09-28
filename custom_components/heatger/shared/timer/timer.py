"""Timer class"""
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util


class Timer:
    """Provide a one-shot timer based on the Home Assistant scheduler.

    The deadline is an absolute point in time, so the timer is not affected by
    long sleeps, clock adjustments or daylight saving time changes.
    """

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._unsub: Optional[Callable[[], None]] = None
        self._end: Optional[datetime] = None

    async def start(self, timeout: float, on_timeout_callback: Callable[[], Awaitable[None]]) -> None:
        """start timer with timeout in seconds, on timeout call on_timeout_callback"""
        await self.start_at(dt_util.utcnow() + timedelta(seconds=max(timeout, 0)), on_timeout_callback)

    async def start_at(self, when: datetime, on_timeout_callback: Callable[[], Awaitable[None]]) -> None:
        """start timer that fires at the given (timezone aware) datetime"""
        await self.stop()
        self._end = dt_util.as_utc(when)

        async def _fire(_now: datetime) -> None:
            # the timer is over: clear it before calling the callback, so the
            # callback can safely start a new timer
            self._unsub = None
            self._end = None
            await on_timeout_callback()

        self._unsub = async_track_point_in_utc_time(self.hass, _fire, self._end)

    async def stop(self) -> None:
        """stop timer"""
        if self._unsub is not None:
            self._unsub()
        self._unsub = None
        self._end = None

    def is_running(self) -> bool:
        """return True if the timer is running"""
        return self._end is not None

    def get_remaining_time(self) -> int:
        """return the remaining time before timeout in seconds, -1 if not running"""
        if self._end is None:
            return -1
        return max(int((self._end - dt_util.utcnow()).total_seconds()), 0)
