"""Binary sensor: a comfort schedule is waiting for someone at home"""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HeatgerZoneEntity, get_season, get_zone_manager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    season = get_season(hass)
    async_add_entities([WaitingPresenceSensor(entry, zone, season)
                        for zone in get_zone_manager(hass, entry).zones])


class WaitingPresenceSensor(HeatgerZoneEntity, BinarySensorEntity):
    """On while the zone waits for someone at home to switch to comfort"""

    _attr_translation_key = 'waiting_presence'

    def __init__(self, entry, zone, season):
        super().__init__(entry, zone, season, 'waiting_presence')

    @property
    def is_on(self) -> bool:
        return self.zone.is_ping
