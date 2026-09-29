"""Base classes of the Heatger entities"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DATA_SEASON, DATA_ZONE_MANAGER, DOMAIN
from .season import SeasonManager
from .zone.zone import Zone
from .zone.zone_manager import ZoneManager


def main_device_info(entry: ConfigEntry) -> DeviceInfo:
    """the Heatger device: server sensors and season"""
    return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name='Heatger', manufacturer='Heatger')


def zone_device_info(entry: ConfigEntry, zone: Zone) -> DeviceInfo:
    """one device per zone"""
    return DeviceInfo(identifiers={(DOMAIN, f'zone_{zone.zone_id}')}, name=f'Heatger {zone.name}',
                      manufacturer='Heatger', model='Zone', via_device=(DOMAIN, entry.entry_id))


def get_zone_manager(hass, entry: ConfigEntry) -> ZoneManager:  # pylint: disable=unused-argument
    return hass.data[DOMAIN][DATA_ZONE_MANAGER]


def get_season(hass) -> SeasonManager:
    return hass.data[DOMAIN][DATA_SEASON]


class HeatgerEntity(Entity):
    """Push entity (no polling) refreshed by listeners"""

    _attr_has_entity_name = True
    _attr_should_poll = False

    @callback
    def _refresh(self) -> None:
        self.async_write_ha_state()


class HeatgerZoneEntity(HeatgerEntity):
    """Entity of a zone: refreshed when the zone or the season changes"""

    def __init__(self, entry: ConfigEntry, zone: Zone, season: SeasonManager, key: str):
        self.zone = zone
        self.season = season
        self._attr_unique_id = f'{zone.zone_id}_{key}'
        self._attr_device_info = zone_device_info(entry, zone)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.zone.listeners.add(self._refresh))
        self.async_on_remove(self.season.listeners.add(self._refresh))


class HeatgerSeasonEntity(HeatgerEntity):
    """Entity of the season, on the main device"""

    def __init__(self, entry: ConfigEntry, season: SeasonManager, key: str):
        self.season = season
        self._attr_unique_id = f'{entry.entry_id}_{key}'
        self._attr_translation_key = key
        self._attr_device_info = main_device_info(entry)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.season.listeners.add(self._refresh))
