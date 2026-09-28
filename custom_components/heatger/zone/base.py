"""Base class"""
import abc
import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.heatger.shared.timer.timer import Timer


class Base(metaclass=abc.ABCMeta):
    """Abstract class Base, necessary for define zone class"""
    def __init__(self, hass: HomeAssistant):
        super().__init__()
        self.hass = hass
        self.timer = Timer(hass)

    @abc.abstractmethod
    async def on_time_out(self) -> None:
        """function called on timeout"""
        raise NotImplementedError

    def get_remaining_time(self) -> int:
        """get remaining time before state change"""
        return self.timer.get_remaining_time()

    @staticmethod
    def get_next_day(weekday: int, hour: datetime.time,
                     now: datetime.datetime = None) -> datetime.datetime:
        """return the next (timezone aware) datetime matching weekday and hour.

        If the given weekday/hour is now or already passed today, the date of next week is returned.
        """
        if now is None:
            now = dt_util.now()
        days_ahead = (weekday - now.weekday()) % 7
        target_date = now.date() + datetime.timedelta(days=days_ahead)
        # combine with the local timezone: the right UTC offset is chosen for this date (DST safe)
        result = datetime.datetime.combine(target_date, datetime.time(hour.hour, hour.minute), tzinfo=now.tzinfo)
        if result.replace(second=0, microsecond=0) <= now.replace(second=0, microsecond=0):
            result = datetime.datetime.combine(target_date + datetime.timedelta(days=7),
                                               datetime.time(hour.hour, hour.minute), tzinfo=now.tzinfo)
        return result

    async def stop_loop(self):
        """Stop the loop"""
        await self.timer.stop()
