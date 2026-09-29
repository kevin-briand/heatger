"""Validation of the configuration of a zone (A3: setpoints consistency and device limits)"""
from __future__ import annotations

from typing import Optional

from homeassistant.core import HomeAssistant

from .actuators.climate import capabilities_of
from .const import ACTUATOR_CLIMATE, ACTUATOR_PILOT_WIRE, SETPOINT_OFF, SETPOINTS_COOL, SETPOINTS_HEAT
from .models import ActuatorConfig, HeatgerConfig, Setpoints, ZoneConfig

SEASON_LABELS = {SETPOINTS_HEAT: 'chauffage', SETPOINTS_COOL: 'climatisation'}
HVAC_FOR = {SETPOINTS_HEAT: 'heat', SETPOINTS_COOL: 'cool'}


def _temperature(value) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def validate_setpoints(key: str, setpoints: Setpoints, capabilities: Optional[dict]) -> list[str]:
    """inversion (eco warmer than comfort when heating, colder when cooling), device limits, presets"""
    errors = []
    label = SEASON_LABELS[key]
    comfort, eco = _temperature(setpoints.comfort), _temperature(setpoints.eco)
    if comfort is not None and eco is not None:
        if key == SETPOINTS_HEAT and eco > comfort:
            errors.append(f'En {label}, la consigne Éco ({eco:g} °C) est plus chaude que le Confort ({comfort:g} °C)')
        if key == SETPOINTS_COOL and eco < comfort:
            errors.append(f'En {label}, la consigne Éco ({eco:g} °C) est plus froide que le Confort ({comfort:g} °C)')
    if capabilities is None:
        return errors
    if HVAC_FOR[key] not in capabilities['hvac_modes']:
        errors.append(f"L'appareil ne sait pas faire le mode {HVAC_FOR[key]} ({label})")
    for name, value in (('Confort', setpoints.comfort), ('Éco', setpoints.eco)):
        temperature = _temperature(value)
        if temperature is not None:
            low, high = capabilities.get('min_temp'), capabilities.get('max_temp')
            if (low is not None and temperature < float(low)) or (high is not None and temperature > float(high)):
                errors.append(f'{name} {label} : {temperature:g} °C hors des limites de l\'appareil ({low}–{high} °C)')
        elif isinstance(value, dict) and value['preset'] not in capabilities['preset_modes']:
            errors.append(f"{name} {label} : le preset « {value['preset']} » n'existe pas sur l'appareil")
    return errors


def validate_actuator(hass: HomeAssistant, actuator: ActuatorConfig) -> list[str]:
    if actuator.type == ACTUATOR_PILOT_WIRE:
        return []
    errors = []
    if actuator.heat is None and actuator.cool is None:
        errors.append(f'{actuator.entity_id} : aucune consigne, il ne sera jamais piloté')
    capabilities = capabilities_of(hass.states.get(actuator.entity_id))
    for key in (SETPOINTS_HEAT, SETPOINTS_COOL):
        setpoints = actuator.setpoints(key)
        if setpoints is not None:
            errors += [f'{actuator.entity_id} : {error}' for error in validate_setpoints(key, setpoints, capabilities)]
    return errors


def validate_zone(hass: HomeAssistant, zone: ZoneConfig, config: HeatgerConfig) -> list[str]:
    """errors of the zone, checked against the other zones of the config"""
    errors = []
    if not zone.name:
        errors.append('La zone doit avoir un nom')
    others = [other for other in config.zones if other.id != zone.id]
    if any(other.name == zone.name for other in others):
        errors.append(f'Une autre zone s\'appelle déjà « {zone.name} »')
    used_outputs = {a.output for other in others for a in other.actuators if a.type == ACTUATOR_PILOT_WIRE}
    used_entities = {a.entity_id for other in others for a in other.actuators if a.type == ACTUATOR_CLIMATE}
    seen = set()
    for actuator in zone.actuators:
        key = actuator.output if actuator.type == ACTUATOR_PILOT_WIRE else actuator.entity_id
        if key in seen:
            errors.append(f'{key} est utilisé deux fois dans la zone')
        seen.add(key)
        if key in used_outputs or key in used_entities:
            errors.append(f'{key} est déjà utilisé par une autre zone')
        errors += validate_actuator(hass, actuator)
    if zone.temperature_sensor and not zone.temperature_sensor.startswith('sensor.'):
        errors.append('Le capteur de température doit être une entité sensor')
    return errors


def validate_setpoint_change(actuator: ActuatorConfig, key: str, state_key: str, value: float,
                             capabilities: Optional[dict]) -> list[str]:
    """validation of a single setpoint changed from a number entity"""
    current = actuator.setpoints(key)
    comfort = value if state_key == 'comfort' else current.comfort
    eco = value if state_key == 'eco' else current.eco
    return validate_setpoints(key, Setpoints(comfort, eco), capabilities)


__all__ = ['validate_zone', 'validate_actuator', 'validate_setpoints', 'validate_setpoint_change', 'SETPOINT_OFF']
