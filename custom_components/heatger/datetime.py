"""Datetime entity: end of the programmed season"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HeatgerSeasonEntity, get_season


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SeasonEnd(entry, get_season(hass))])


class SeasonEnd(HeatgerSeasonEntity, DateTimeEntity):
    """End of the current season, then the next season applies (empty = not programmed)"""

    def __init__(self, entry, season):
        super().__init__(entry, season, 'season_end')

    @property
    def native_value(self) -> Optional[datetime]:
        return self.season.until

    async def async_set_value(self, value: datetime) -> None:
        await self.season.async_set_until(value)
