"""Actuators: translate the state of a zone and the season into orders for a device"""
from homeassistant.core import HomeAssistant

from ..const import ACTUATOR_CLIMATE
from ..models import ActuatorConfig
from ..storage import HeatgerStorage
from .base import Actuator
from .climate import ClimateActuator
from .pilot_wire import PilotWireActuator


def create_actuator(hass: HomeAssistant, storage: HeatgerStorage, config: ActuatorConfig) -> Actuator:
    """return the actuator matching the config type"""
    if config.type == ACTUATOR_CLIMATE:
        return ClimateActuator(hass, storage, config)
    return PilotWireActuator(hass, storage, config)
