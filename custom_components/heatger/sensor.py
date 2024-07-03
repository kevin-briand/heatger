"""sensor class"""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfPressure, \
    PERCENTAGE

from custom_components.heatger import DOMAIN, WSClient
from custom_components.heatger.coordinator import SensorCoordinator


async def async_setup_entry(hass, config, async_add_entities):
    """Initialize and register sensors"""
    ws: WSClient = hass.data[DOMAIN]['WS']
    server_config = await ws.get_config()

    temp_coordinator = SensorCoordinator(hass)
    em_coordinator = SensorCoordinator(hass)
    hass.data[DOMAIN]['temp_coordinator'] = temp_coordinator
    hass.data[DOMAIN]['em_coordinator'] = em_coordinator

    # register sensors
    if server_config['i2c']['temperature']['enabled']:
        async_add_entities([
            TemperatureEntity(temp_coordinator),
            HumidityEntity(temp_coordinator),
            PressureEntity(temp_coordinator),
        ])
    if server_config['entry']['electric_meter']['enabled']:
        async_add_entities([
            ElectricMeterEntity(em_coordinator)
        ])

    return True


class BaseEntity(CoordinatorEntity, Entity):
    def __init__(self, name: str, coordinator: SensorCoordinator):
        """temperature sensor"""
        super().__init__(coordinator=coordinator)
        self.entity_id = f'sensor.heatger_{name}'
        self._attr_unique_id = f'heatger_{name}'
        self._name = name
        self._state = None

    @property
    def state(self):
        """return the actual state of the sensor"""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return
        self._state = data[self._name]
        self.async_write_ha_state()


class TemperatureEntity(BaseEntity):
    device_class = SensorDeviceClass.TEMPERATURE
    unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: SensorCoordinator):
        """temperature sensor"""
        super().__init__('temperature', coordinator)


class HumidityEntity(BaseEntity):
    device_class = SensorDeviceClass.HUMIDITY
    unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: SensorCoordinator):
        """Humidity sensor"""
        super().__init__('humidity', coordinator)


class PressureEntity(BaseEntity):
    device_class = SensorDeviceClass.PRESSURE
    unit_of_measurement = UnitOfPressure.HPA

    def __init__(self, coordinator: SensorCoordinator):
        """Pressure sensor"""
        super().__init__('pressure', coordinator)


class ElectricMeterEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: SensorCoordinator):
        """electric meter sensor"""
        super().__init__(coordinator)
        self.entity_id = 'sensor.heatger_electric_meter'
        self._attr_unique_id = 'heatger_electric_meter'
        self._name = 'electric_meter'
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_state_class = 'total_increasing'
        self._state = None

    @property
    def native_value(self):
        """return the actual state of the sensor"""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return
        self._state = data[self._name]
        self.async_write_ha_state()
