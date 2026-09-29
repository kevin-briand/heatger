"""Number entities: the temperature setpoints of the thermostat actuators"""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .actuators.climate import ClimateActuator
from .const import DATA_STORAGE, DOMAIN, SETPOINTS_COOL, SETPOINTS_HEAT
from .entity import HeatgerZoneEntity, get_season, get_zone_manager
from .validation import validate_setpoint_change

DEFAULT_MIN = 5.0
DEFAULT_MAX = 35.0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    season = get_season(hass)
    entities = []
    for zone in get_zone_manager(hass, entry).zones:
        for actuator in zone.actuators:
            if not isinstance(actuator, ClimateActuator):
                continue
            for key in (SETPOINTS_HEAT, SETPOINTS_COOL):
                setpoints = actuator.config.setpoints(key)
                if setpoints is None:
                    continue
                for state_key in ('comfort', 'eco'):
                    value = getattr(setpoints, state_key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        entities.append(SetpointNumber(entry, zone, season, actuator, key, state_key))
    async_add_entities(entities)


class SetpointNumber(HeatgerZoneEntity, NumberEntity):
    """A temperature setpoint of a thermostat actuator, for a season and a state"""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, zone, season, actuator: ClimateActuator, key: str, state_key: str):
        super().__init__(entry, zone, season, f'{actuator.id}_{key}_{state_key}')
        self.actuator = actuator
        self.key = key
        self.state_key = state_key
        self._attr_translation_key = f'setpoint_{key}_{state_key}'
        self._attr_translation_placeholders = {'actuator': actuator.config.name or actuator.entity_id}

    def _limit(self, name: str, default: float) -> float:
        capabilities = self.actuator.capabilities()
        if capabilities and capabilities.get(name) is not None:
            return float(capabilities[name])
        return default

    @property
    def native_min_value(self) -> float:
        return self._limit('min_temp', DEFAULT_MIN)

    @property
    def native_max_value(self) -> float:
        return self._limit('max_temp', DEFAULT_MAX)

    @property
    def available(self) -> bool:
        value = getattr(self.actuator.config.setpoints(self.key), self.state_key, None)
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @property
    def native_value(self):
        setpoints = self.actuator.config.setpoints(self.key)
        return getattr(setpoints, self.state_key) if setpoints else None

    async def async_set_native_value(self, value: float) -> None:
        errors = validate_setpoint_change(self.actuator.config, self.key, self.state_key, value,
                                          self.actuator.capabilities())
        if errors:
            raise ServiceValidationError(' ; '.join(errors))
        setpoints = self.actuator.config.setpoints(self.key)
        setattr(setpoints, self.state_key, float(value))
        await self.hass.data[DOMAIN][DATA_STORAGE].async_save_config()
        # applied now if the current state uses it (unless the device was set manually)
        await self.actuator.reapply()
        self.async_write_ha_state()
