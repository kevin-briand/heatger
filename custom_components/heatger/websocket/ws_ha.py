"""Websocket commands used by the Heatger panel and card"""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components.websocket_api import async_register_command, decorators
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from ..actuators.climate import capabilities_of
from ..const import (ACTUATOR_CLIMATE, DATA_ENTRY, DATA_SEASON, DATA_STORAGE, DATA_ZONE_MANAGER, DOMAIN,
                     SETPOINTS_COOL, SETPOINTS_HEAT)
from ..models import HeatgerError, Setpoints, ZoneConfig
from ..panel import RELOADING
from ..validation import validate_setpoints, validate_zone


def _data(hass: HomeAssistant) -> dict:
    data = hass.data.get(DOMAIN)
    if not data or DATA_ZONE_MANAGER not in data:
        raise HeatgerError('Heatger is not loaded')
    return data


def schedule_reload(hass: HomeAssistant) -> None:
    """the zones or the actuators changed: the entities are created again"""
    entry = _data(hass)[DATA_ENTRY]
    hass.data[RELOADING] = True  # the panel stays open during the reload
    hass.config_entries.async_schedule_reload(entry.entry_id)


def _error(connection, msg_id, error: Exception) -> None:
    connection.send_error(msg_id, 'heatger_error', str(error))


# ---- read (panel + card)

@callback
@decorators.websocket_command({vol.Required("type"): "heatger/config"})
@decorators.async_response
async def handle_get_config(hass: HomeAssistant, connection, msg):
    """whole configuration + live state of the zones + season"""
    try:
        data = _data(hass)
    except HeatgerError as e:
        _error(connection, msg["id"], e)
        return
    manager = data[DATA_ZONE_MANAGER]
    zones = []
    for zone_config in data[DATA_STORAGE].config.zones:
        zone = manager.zone_or_none(zone_config.id)
        zones.append({**zone_config.to_dict(), 'live': zone.get_data() if zone else None})
    connection.send_result(msg["id"], {
        'zones': zones,
        'users': data[DATA_STORAGE].config.users,
        'season': data[DATA_SEASON].get_info(),
    })


@callback
@decorators.websocket_command({vol.Required("type"): "heatger/climate_entities"})
@decorators.async_response
async def handle_climate_entities(hass: HomeAssistant, connection, msg):
    """climate entities of Home Assistant and their capabilities (panel: thermostat actuators)"""
    result = []
    for state in hass.states.async_all('climate'):
        if state.entity_id.startswith(f'climate.{DOMAIN}_') or state.attributes.get('zone_id'):
            continue  # the zones of heatger itself
        capabilities = capabilities_of(state)
        result.append({'entity_id': state.entity_id,
                       'name': state.attributes.get('friendly_name', state.entity_id),
                       'available': capabilities is not None,
                       **(capabilities or {'hvac_modes': [], 'preset_modes': [], 'min_temp': None,
                                           'max_temp': None})})
    result.sort(key=lambda item: item['name'].lower())
    connection.send_result(msg["id"], result)


@callback
@decorators.websocket_command({vol.Required("type"): "heatger/season"})
@decorators.async_response
async def handle_get_season(hass: HomeAssistant, connection, msg):
    try:
        connection.send_result(msg["id"], _data(hass)[DATA_SEASON].get_info())
    except HeatgerError as e:
        _error(connection, msg["id"], e)


@callback
@decorators.websocket_command({vol.Required("type"): "heatger_get_zones_info"})
@decorators.async_response
async def handle_get_zones_info(hass: HomeAssistant, connection, msg):
    """live state of the zones (card)"""
    try:
        result = await _data(hass)[DATA_ZONE_MANAGER].get_zones_info()
    except HeatgerError:
        result = {}
    connection.send_result(msg["id"], result)


@callback
@decorators.websocket_command({vol.Required("type"): "heatger_get_frostfree_info"})
@decorators.async_response
async def handle_get_frostfree_info(hass: HomeAssistant, connection, msg):
    """compatibility with the version 1 of the card: remaining time of the season stop"""
    try:
        result = await _data(hass)[DATA_ZONE_MANAGER].get_frostfree_info()
    except HeatgerError:
        result = -1
    connection.send_result(msg["id"], result)


@callback
@decorators.websocket_command({vol.Required("type"): "heatger_get_zones"})
@decorators.async_response
async def handle_get_zones(hass: HomeAssistant, connection, msg):
    """zones config by id"""
    try:
        zones = _data(hass)[DATA_STORAGE].config.zones
    except HeatgerError:
        zones = []
    connection.send_result(msg["id"], {zone.id: zone.to_dict() for zone in zones})


@callback
@decorators.websocket_command({vol.Required("type"): "heatger_get_available_persons"})
@decorators.async_response
async def handle_get_available_persons(hass: HomeAssistant, connection, msg):
    connection.send_result(msg["id"], hass.states.async_all('person'))


@callback
@decorators.websocket_command({vol.Required("type"): "heatger_get_selected_persons"})
@decorators.async_response
async def handle_get_selected_persons(hass: HomeAssistant, connection, msg):
    try:
        users = _data(hass)[DATA_STORAGE].config.users
    except HeatgerError:
        users = []
    connection.send_result(msg["id"], users)


# ---- write (panel, admin only)

@callback
@decorators.websocket_command({vol.Required("type"): "heatger/zone/save", vol.Required("zone"): dict})
@decorators.require_admin
@decorators.async_response
async def handle_save_zone(hass: HomeAssistant, connection, msg):
    """create or update a zone (name, enabled, actuators, temperature sensor); the programs are kept"""
    try:
        data = _data(hass)
        storage = data[DATA_STORAGE]
        raw = dict(msg['zone'])
        existing = next((z for z in storage.config.zones if raw.get('id') and z.id == raw['id']), None)
        if existing is not None:
            raw['programs'] = {key: [s.to_dict() for s in value] for key, value in existing.programs.items()}
        zone = ZoneConfig.from_dict(raw)
    except HeatgerError as e:
        connection.send_result(msg["id"], {'success': False, 'errors': [str(e)]})
        return
    except (KeyError, TypeError, ValueError) as e:
        connection.send_result(msg["id"], {'success': False, 'errors': [f'Données invalides : {e}']})
        return
    errors = validate_zone(hass, zone, storage.config)
    if errors:
        connection.send_result(msg["id"], {'success': False, 'errors': errors})
        return
    if existing is not None:
        storage.config.zones[storage.config.zones.index(existing)] = zone
    else:
        storage.config.zones.append(zone)
    await storage.async_save_config()
    connection.send_result(msg["id"], {'success': True, 'errors': [], 'id': zone.id})
    schedule_reload(hass)


@callback
@decorators.websocket_command({vol.Required("type"): "heatger/zone/delete", vol.Required("zone_id"): cv.string})
@decorators.require_admin
@decorators.async_response
async def handle_delete_zone(hass: HomeAssistant, connection, msg):
    try:
        storage = _data(hass)[DATA_STORAGE]
        zone = storage.config.get_zone(msg['zone_id'])
    except HeatgerError as e:
        _error(connection, msg["id"], e)
        return
    storage.config.zones.remove(zone)
    storage.persist.zones.pop(zone.id, None)
    for actuator in zone.actuators:
        storage.persist.actuators_off.pop(actuator.id, None)
        if actuator.id in storage.persist.known_actuators:
            storage.persist.known_actuators.remove(actuator.id)
    await storage.async_save_config()
    await storage.async_save_persist()
    connection.send_result(msg["id"], {'success': True})
    schedule_reload(hass)


@callback
@decorators.websocket_command({vol.Required("type"): "heatger/zone/move", vol.Required("zone_id"): cv.string,
                               vol.Required("offset"): vol.In([-1, 1])})
@decorators.require_admin
@decorators.async_response
async def handle_move_zone(hass: HomeAssistant, connection, msg):
    """change the order of the zones (the order gives the zone numbers of the toggle service)"""
    try:
        storage = _data(hass)[DATA_STORAGE]
        zone = storage.config.get_zone(msg['zone_id'])
    except HeatgerError as e:
        _error(connection, msg["id"], e)
        return
    zones = storage.config.zones
    index = zones.index(zone)
    target = index + msg['offset']
    if 0 <= target < len(zones):
        zones[index], zones[target] = zones[target], zones[index]
        await storage.async_save_config()
        schedule_reload(hass)
    connection.send_result(msg["id"], {'success': True})


def _numeric(setpoints: Setpoints) -> tuple[bool, bool]:
    """which setpoints are temperatures (they have a number entity)"""
    return tuple(isinstance(v, float) for v in (setpoints.comfort, setpoints.eco))


@callback
@decorators.websocket_command({vol.Required("type"): "heatger/setpoints/save", vol.Required("actuator_id"): cv.string,
                               vol.Required("key"): vol.In([SETPOINTS_HEAT, SETPOINTS_COOL]),
                               vol.Required("setpoints"): dict})
@decorators.require_admin
@decorators.async_response
async def handle_save_setpoints(hass: HomeAssistant, connection, msg):
    """change the comfort / eco setpoints of a thermostat for a season, applied at once (no reload of heatger,
    unless a temperature becomes a preset or the reverse: the number entities are then created again)"""
    try:
        data = _data(hass)
        storage = data[DATA_STORAGE]
        _, config = storage.config.find_actuator(msg['actuator_id'])
        if config.type != ACTUATOR_CLIMATE:
            raise HeatgerError("Cet équipement n'a pas de consignes")
        current = config.setpoints(msg['key'])
        if current is None:
            raise HeatgerError("Cet équipement n'est pas piloté pendant cette saison")
        new = Setpoints.from_dict(msg['setpoints'])
        if new is None:
            raise HeatgerError('Consignes manquantes')
    except (HeatgerError, KeyError, TypeError) as e:
        connection.send_result(msg["id"], {'success': False, 'errors': [str(e)]})
        return
    errors = validate_setpoints(msg['key'], new, capabilities_of(hass.states.get(config.entity_id)))
    if errors:
        connection.send_result(msg["id"], {'success': False, 'errors': errors})
        return
    reload = _numeric(current) != _numeric(new)
    config.set_setpoints(msg['key'], new)
    await storage.async_save_config()
    zone, actuator = data[DATA_ZONE_MANAGER].find_actuator(config.id)
    if actuator is not None and not reload:
        actuator.config.set_setpoints(msg['key'], new)
        await actuator.reapply()  # applied now if the current state uses it (unless set manually)
        await zone.listeners.notify()  # number entities
    connection.send_result(msg["id"], {'success': True, 'errors': [], 'reload': reload})
    if reload:
        schedule_reload(hass)


COMMANDS = [handle_get_config, handle_climate_entities, handle_get_season, handle_get_zones_info,
            handle_get_frostfree_info, handle_get_zones, handle_get_available_persons, handle_get_selected_persons,
            handle_save_zone, handle_delete_zone, handle_move_zone, handle_save_setpoints]


async def async_register_ws(hass):
    for command in COMMANDS:
        async_register_command(hass, command)
