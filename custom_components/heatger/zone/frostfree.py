"""Frostfree class"""
from datetime import datetime
from typing import Callable, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.heatger.local_storage.persistence.persistence import Persistence
from custom_components.heatger.shared.logs.logs import Logs
from custom_components.heatger.zone.base import Base
from custom_components.heatger.zone.zone import Zone

CLASSNAME = 'Frost free'


class Frostfree(Base):
    """this class manage zone class, stop it if started and resume if stopped or timeout"""

    def __init__(self, hass: HomeAssistant, get_zones: Callable[[], list[Zone]]):
        """
        :param get_zones: return the current list of zones (the list is rebuilt when the config changes)
        """
        super().__init__(hass)
        self.get_zones = get_zones
        self.end_date: Optional[datetime] = None
        self._initialized = False

    async def async_init(self):
        """Initialize state of class"""
        if self._initialized:
            return
        await self.restore()
        self._initialized = True

    async def restore(self) -> None:
        """resume frost-free if device restarted"""
        end_date = Persistence(self.hass).get_frost_free_end_date()
        if end_date and end_date > dt_util.now():
            await self.start(end_date)
        elif end_date:
            await self.stop()

    def is_active(self) -> bool:
        """return True if frost-free is active"""
        return self.end_date is not None

    async def on_time_out(self) -> None:
        """called when the timer ended"""
        await self.stop()

    async def start(self, end_date: datetime) -> None:
        """Start frost-free with end date (timezone aware)"""
        await self.timer.start_at(end_date, self.on_time_out)
        await Persistence(self.hass).set_frost_free_end_date(end_date)
        self.end_date = end_date
        Logs.info(CLASSNAME, F'Start frost free until {dt_util.as_local(end_date).isoformat()}')
        for zone in self.get_zones():
            await zone.set_frostfree(True)

    async def stop(self) -> None:
        """stop frost-free"""
        await self.timer.stop()
        self.end_date = None
        await Persistence(self.hass).set_frost_free_end_date()
        Logs.info(CLASSNAME, 'Stop frost free')
        for zone in self.get_zones():
            await zone.set_frostfree(False)

    def get_data(self) -> int:
        """return remaining time in seconds, -1 if frost-free is not active"""
        return self.get_remaining_time()
