"""Heatger services: toggle (v1), set_zone_state, set_season"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (DATA_SEASON, DATA_ZONE_MANAGER, DOMAIN, SERVICE_SET_SEASON, SERVICE_SET_ZONE_STATE,
                    SERVICE_TOGGLE)
from .models import HeatgerError
from .season import SeasonManager
from .shared.enum.mode import Mode
from .shared.enum.season import Season
from .shared.enum.state import State
from .zone.zone_manager import ZoneManager

STATE_PROGRAM = 'program'
STATES = {'comfort': State.COMFORT, 'eco': State.ECO}

TOGGLE_SCHEMA = vol.Schema({
    vol.Required('zone'): cv.positive_int,
    vol.Required('type'): vol.In(['state', 'mode']),
})
SET_ZONE_STATE_SCHEMA = vol.Schema({
    vol.Required('zone'): cv.string,
    vol.Required('state'): vol.In([*STATES, STATE_PROGRAM]),
    vol.Optional('duration'): cv.positive_time_period,
})
SET_SEASON_SCHEMA = vol.Schema({
    vol.Required('season'): vol.In([season.value for season in Season]),
    vol.Optional('until'): cv.datetime,
    vol.Optional('next'): vol.In([season.value for season in Season]),
})


def _zone_manager(hass: HomeAssistant) -> ZoneManager:
    manager = hass.data.get(DOMAIN, {}).get(DATA_ZONE_MANAGER)
    if manager is None:
        raise ServiceValidationError('Heatger is not loaded')
    return manager


def _get_zone(hass: HomeAssistant, zone_id: str):
    try:
        return _zone_manager(hass).get_zone(str(zone_id))
    except HeatgerError as e:
        raise ServiceValidationError(str(e)) from e


async def _toggle(hass: HomeAssistant, call: ServiceCall) -> None:
    """v1 service: toggle the state (until the next schedule) or the mode of the zone number N"""
    try:
        zone = _zone_manager(hass).get_zone_by_number(call.data['zone'])
    except HeatgerError as e:
        raise ServiceValidationError(str(e)) from e
    if call.data['type'] == 'mode':
        await zone.toggle_mode()
    else:
        await zone.toggle_state()


async def _set_zone_state(hass: HomeAssistant, call: ServiceCall) -> None:
    """comfort / eco until the next schedule or for a duration (auto mode), or the manual state (manual mode);
    program = back to the program"""
    zone = _get_zone(hass, call.data['zone'])
    if call.data['state'] == STATE_PROGRAM:
        if zone.mode == Mode.MANUAL:
            await zone.set_mode(Mode.AUTO)
        else:
            await zone.clear_override()
        return
    duration = call.data.get('duration')
    until = dt_util.now() + duration if duration else None
    await zone.set_override(STATES[call.data['state']], until)


async def _set_season(hass: HomeAssistant, call: ServiceCall) -> None:
    season: SeasonManager = hass.data.get(DOMAIN, {}).get(DATA_SEASON)
    if season is None:
        raise ServiceValidationError('Heatger is not loaded')
    until = call.data.get('until')
    if until is not None:
        until = dt_util.as_local(until) if until.tzinfo else until.replace(tzinfo=dt_util.now().tzinfo)
        if until <= dt_util.now():
            raise ServiceValidationError('The end date of the season must be in the future')
    next_season = Season(call.data['next']) if call.data.get('next') else None
    await season.async_set(Season(call.data['season']), until, next_season)


def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_SEASON):
        return

    async def toggle(call: ServiceCall) -> None:
        await _toggle(hass, call)

    async def set_zone_state(call: ServiceCall) -> None:
        await _set_zone_state(hass, call)

    async def set_season(call: ServiceCall) -> None:
        await _set_season(hass, call)

    hass.services.async_register(DOMAIN, SERVICE_TOGGLE, toggle, schema=TOGGLE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_ZONE_STATE, set_zone_state, schema=SET_ZONE_STATE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_SEASON, set_season, schema=SET_SEASON_SCHEMA)


def async_unregister_services(hass: HomeAssistant) -> None:
    for service in (SERVICE_TOGGLE, SERVICE_SET_ZONE_STATE, SERVICE_SET_SEASON):
        hass.services.async_remove(DOMAIN, service)
