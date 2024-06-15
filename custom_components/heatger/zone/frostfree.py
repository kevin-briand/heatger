"""Frostfree class"""
from datetime import datetime
from typing import Optional

from custom_components.heatger.local_storage.persistence.persistence import Persistence
from custom_components.heatger.shared.logs.logs import Logs
from custom_components.heatger.zone.base import Base
from custom_components.heatger.zone.zone import Zone

CLASSNAME = 'Frost free'


class Frostfree(Base):
    """this class manage zone class, stop it if started and resume if stopped or timeout"""
    _initialized = False

    def __init__(self, hass, zones: [Zone]):
        super().__init__()
        self.hass = hass
        Logs.info(CLASSNAME, 'Init...')
        self.zones = zones
        self.end_date: Optional[datetime] = None
        Logs.info(CLASSNAME, 'Started !')

    async def async_init(self):
        """Initialize state of class"""
        if Frostfree._initialized:
            return
        await self.restore()
        Frostfree._initialized = True

    async def restore(self) -> None:
        """resume frost-free if device restarted"""
        end_date = Persistence(self.hass).get_frost_free_end_date()
        if end_date and end_date > datetime.now():
            await self.start(end_date)
        else:
            await self.stop()

    async def on_time_out(self) -> None:
        """called when the timer ended"""
        await self.timer.stop()
        for zone in self.zones:
            Logs.info(zone.zone_id, 'Stop frost free')
            await zone.set_frostfree(False)

    async def start(self, end_date: datetime) -> None:
        """Start frost-free with end date"""
        remaining_time = end_date.timestamp() - datetime.now().timestamp()
        await self.timer.start(remaining_time, self.stop)
        await Persistence(self.hass).set_frost_free_end_date(end_date)
        self.end_date = end_date
        for zone in self.zones:
            Logs.info(zone.zone_id, 'Start frost free')
            await zone.set_frostfree(True)

    async def stop(self) -> None:
        """stop frost-free"""
        await self.on_time_out()
        self.end_date = None
        await Persistence(self.hass).set_frost_free_end_date()

    def get_data(self) -> int:
        """return remaining time in json object"""
        return self.get_remaining_time()
