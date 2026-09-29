"""One climate entity per zone: mode auto (program) / manual, preset comfort / eco"""
from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.climate import (ClimateEntity, ClimateEntityFeature, HVACMode, PRESET_COMFORT,
                                              PRESET_ECO)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .entity import HeatgerZoneEntity, get_season, get_zone_manager
from .shared.enum.mode import Mode
from .shared.enum.season import Season
from .shared.enum.state import State

MANUAL_MODES = {Season.HEATING: HVACMode.HEAT, Season.COOLING: HVACMode.COOL}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    zone_manager = get_zone_manager(hass, entry)
    season = get_season(hass)
    async_add_entities([HeatgerZoneClimate(entry, zone, season) for zone in zone_manager.zones])


class HeatgerZoneClimate(HeatgerZoneEntity, ClimateEntity):
    """The zone as a thermostat: hvac mode auto = program, heat/cool = manual; preset = state"""

    _attr_name = None
    _attr_translation_key = 'zone'
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO]
    _attr_supported_features = ClimateEntityFeature.PRESET_MODE

    def __init__(self, entry, zone, season):
        super().__init__(entry, zone, season, 'climate')

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        sensor = self.zone.config.temperature_sensor
        if sensor:
            self.async_on_remove(async_track_state_change_event(self.hass, [sensor], self._on_sensor))

    @callback
    def _on_sensor(self, _event: Event) -> None:
        self.async_write_ha_state()

    @property
    def hvac_modes(self) -> list[HVACMode]:
        if self.season.current == Season.STOP:
            return [HVACMode.OFF]
        return [HVACMode.AUTO, MANUAL_MODES[self.season.current]]

    @property
    def hvac_mode(self) -> HVACMode:
        if self.season.current == Season.STOP:
            return HVACMode.OFF
        if self.zone.mode == Mode.AUTO:
            return HVACMode.AUTO
        return MANUAL_MODES[self.season.current]

    @property
    def preset_mode(self) -> str:
        return PRESET_COMFORT if self.zone.current_state == State.COMFORT else PRESET_ECO

    @property
    def current_temperature(self) -> Optional[float]:
        sensor = self.zone.config.temperature_sensor
        state = self.hass.states.get(sensor) if sensor else None
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            'zone_id': self.zone.zone_id,
            'season': self.season.current.value,
            'waiting_presence': self.zone.is_ping,
            'next_change': self.zone.next_change.isoformat() if self.zone.next_change else None,
            'override_until': self.zone.override_until.isoformat() if self.zone.override_until else None,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF or self.season.current == Season.STOP:
            raise ServiceValidationError('Heatger: the zones are stopped by the season "stop", change the season')
        await self.zone.set_mode(Mode.AUTO if hvac_mode == HVACMode.AUTO else Mode.MANUAL)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        state = State.COMFORT if preset_mode == PRESET_COMFORT else State.ECO
        await self.zone.set_override(state)
