"""sensor class"""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfPressure, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SensorCoordinator


def _is_enabled(server_config: dict, *keys: str) -> bool:
    """return True if server_config[keys...]['enabled'] is True"""
    node = server_config or {}
    for key in keys:
        node = node.get(key) or {}
    return bool(node.get('enabled'))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Initialize and register sensors"""
    server_config = hass.data[DOMAIN].get('server_config') or {}

    temp_coordinator = SensorCoordinator(hass, entry)
    em_coordinator = SensorCoordinator(hass, entry)
    hass.data[DOMAIN]['temp_coordinator'] = temp_coordinator
    hass.data[DOMAIN]['em_coordinator'] = em_coordinator

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name='Heatger',
        manufacturer='Heatger',
    )

    entities = []
    if _is_enabled(server_config, 'i2c', 'temperature'):
        entities += [
            HeatgerSensor(temp_coordinator, device_info, 'temperature', SensorDeviceClass.TEMPERATURE,
                          UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
            HeatgerSensor(temp_coordinator, device_info, 'humidity', SensorDeviceClass.HUMIDITY,
                          PERCENTAGE, SensorStateClass.MEASUREMENT),
            HeatgerSensor(temp_coordinator, device_info, 'pressure', SensorDeviceClass.PRESSURE,
                          UnitOfPressure.HPA, SensorStateClass.MEASUREMENT),
        ]
    if _is_enabled(server_config, 'entry', 'electric_meter'):
        entities.append(
            HeatgerSensor(em_coordinator, device_info, 'electric_meter', SensorDeviceClass.ENERGY,
                          UnitOfEnergy.WATT_HOUR, SensorStateClass.TOTAL_INCREASING)
        )
    async_add_entities(entities)


class HeatgerSensor(CoordinatorEntity, SensorEntity):
    """Sensor pushed by the heatger server"""

    def __init__(self, coordinator: SensorCoordinator, device_info: DeviceInfo, key: str,
                 device_class: SensorDeviceClass, unit: str, state_class: SensorStateClass):
        super().__init__(coordinator)
        # keep the historical ids, so the existing history and automations still work
        self.entity_id = f'sensor.heatger_{key}'
        self._attr_unique_id = f'heatger_{key}'
        self._attr_name = f'Heatger {key.replace("_", " ")}'
        self._attr_device_info = device_info
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._key = key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data or self._key not in data:
            return
        self._attr_native_value = data[self._key]
        self.async_write_ha_state()
