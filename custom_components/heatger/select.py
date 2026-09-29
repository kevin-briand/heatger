"""Select entities: the season, and the season following a programmed end"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HeatgerSeasonEntity, get_season
from .shared.enum.season import Season

OPTIONS = [season.value for season in Season]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    season = get_season(hass)
    async_add_entities([SeasonSelect(entry, season), NextSeasonSelect(entry, season)])


class SeasonSelect(HeatgerSeasonEntity, SelectEntity):
    """Current season, choosing one cancels a programmed end"""

    _attr_options = OPTIONS

    def __init__(self, entry, season):
        super().__init__(entry, season, 'season')

    @property
    def current_option(self) -> str:
        return self.season.current.value

    async def async_select_option(self, option: str) -> None:
        await self.season.async_set(Season(option))


class NextSeasonSelect(HeatgerSeasonEntity, SelectEntity):
    """Season applied at the end of the programmed season"""

    _attr_options = OPTIONS

    def __init__(self, entry, season):
        super().__init__(entry, season, 'season_next')

    @property
    def current_option(self) -> str:
        return self.season.next.value

    async def async_select_option(self, option: str) -> None:
        await self.season.async_set_until(self.season.until, Season(option))
