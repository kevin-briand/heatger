"""HTTP endpoints used by the Heatger panel (programs, persons, zones) and the card (season stop)"""
from __future__ import annotations

from functools import wraps
from http import HTTPStatus

import voluptuous as vol
from homeassistant.components.http.data_validator import RequestDataValidator
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.util import dt as dt_util

from ..const import DATA_SEASON, DATA_STORAGE, DATA_ZONE_MANAGER, DOMAIN, PROGRAM_WINTER, PROGRAMS
from ..models import HeatgerError, Schedule, ZoneConfig, sort_schedules, str_to_datetime
from ..shared.enum.season import Season
from ..shared.enum.state import State
from ..websocket.ws_ha import schedule_reload

DAYS = [0, 1, 2, 3, 4, 5, 6]
STATES = [State.COMFORT.value, State.ECO.value]
SCHEDULE_SCHEMA = {
    vol.Required('day'): vol.In(DAYS),
    vol.Required('hour'): cv.string,
    vol.Required('state'): vol.In(STATES),
}


def handle_errors(func):
    """Return a clean json error instead of a 500 error"""
    @wraps(func)
    async def wrapper(view: HomeAssistantView, request, *args, **kwargs):
        if request.app["hass"].data.get(DOMAIN, {}).get(DATA_ZONE_MANAGER) is None:
            return view.json_message('Heatger is not loaded', HTTPStatus.SERVICE_UNAVAILABLE)
        try:
            return await func(view, request, *args, **kwargs)
        except HeatgerError as e:
            return view.json_message(str(e), HTTPStatus.BAD_REQUEST)
        except (KeyError, ValueError) as e:
            return view.json_message(f'Invalid data: {e}', HTTPStatus.BAD_REQUEST)
    return wrapper


def _storage(request):
    return request.app["hass"].data[DOMAIN][DATA_STORAGE]


async def _program_changed(request, zone_id: str) -> None:
    """save the config and compute again the state of the zone"""
    hass = request.app["hass"]
    await hass.data[DOMAIN][DATA_STORAGE].async_save_config()
    zone = hass.data[DOMAIN][DATA_ZONE_MANAGER].zone_or_none(zone_id)
    if zone is not None:
        await zone.refresh()


class HeatgerAddProgView(HomeAssistantView):
    """Add schedules to the program of a zone (program: winter / summer)"""

    url = "/api/heatger/prog/add"
    name = "api:heatger:prog:add"

    @RequestDataValidator(vol.Schema({
        vol.Required('zone_id'): cv.string,
        vol.Optional('program', default=PROGRAM_WINTER): vol.In(PROGRAMS),
        vol.Required('prog'): vol.All(cv.ensure_list, [SCHEDULE_SCHEMA]),
    }))
    @handle_errors
    async def post(self, request, data):
        zone = _storage(request).config.get_zone(data['zone_id'])
        program = zone.programs[data['program']]
        for raw in data['prog']:
            schedule = Schedule.from_dict(raw)
            if schedule in program:
                program.remove(schedule)
            program.append(schedule)
        zone.programs[data['program']] = sort_schedules(program)
        await _program_changed(request, zone.id)
        return self.json({"success": True})


class HeatgerRemoveProgView(HomeAssistantView):
    """Remove a schedule from the program of a zone"""

    url = "/api/heatger/prog/remove"
    name = "api:heatger:prog:remove"

    @RequestDataValidator(vol.Schema({
        vol.Required('zone_id'): cv.string,
        vol.Optional('program', default=PROGRAM_WINTER): vol.In(PROGRAMS),
        vol.Required('prog'): SCHEDULE_SCHEMA,
    }))
    @handle_errors
    async def post(self, request, data):
        zone = _storage(request).config.get_zone(data['zone_id'])
        schedule = Schedule.from_dict(data['prog'])
        program = zone.programs[data['program']]
        if schedule in program:
            program.remove(schedule)
        await _program_changed(request, zone.id)
        return self.json({"success": True})


class HeatgerRemoveAllProgView(HomeAssistantView):
    """Remove all the schedules of a program"""

    url = "/api/heatger/prog/removeall"
    name = "api:heatger:prog:removeall"

    @RequestDataValidator(vol.Schema({
        vol.Required('zone_id'): cv.string,
        vol.Optional('program', default=PROGRAM_WINTER): vol.In(PROGRAMS),
    }))
    @handle_errors
    async def post(self, request, data):
        zone = _storage(request).config.get_zone(data['zone_id'])
        zone.programs[data['program']] = []
        await _program_changed(request, zone.id)
        return self.json({"success": True})


class HeatgerCopyProgView(HomeAssistantView):
    """Copy a program to the other season program of the same zone"""

    url = "/api/heatger/prog/copy"
    name = "api:heatger:prog:copy"

    @RequestDataValidator(vol.Schema({
        vol.Required('zone_id'): cv.string,
        vol.Required('from'): vol.In(PROGRAMS),
        vol.Required('to'): vol.In(PROGRAMS),
    }))
    @handle_errors
    async def post(self, request, data):
        zone = _storage(request).config.get_zone(data['zone_id'])
        zone.programs[data['to']] = [Schedule.from_dict(s.to_dict()) for s in zone.programs[data['from']]]
        await _program_changed(request, zone.id)
        return self.json({"success": True})


class HeatgerAddUserView(HomeAssistantView):
    """Add a person to the presence check"""

    url = "/api/heatger/user/add"
    name = "api:heatger:user:add"

    @RequestDataValidator(vol.Schema({vol.Required('user'): cv.string}))
    @handle_errors
    async def post(self, request, data):
        storage = _storage(request)
        if data['user'] and data['user'] not in storage.config.users:
            storage.config.users.append(data['user'])
            await storage.async_save_config()
        return self.json({"success": True})


class HeatgerRemoveUserView(HomeAssistantView):
    """Remove a person from the presence check"""

    url = "/api/heatger/user/remove"
    name = "api:heatger:user:remove"

    @RequestDataValidator(vol.Schema({vol.Required('user'): cv.string}))
    @handle_errors
    async def post(self, request, data):
        storage = _storage(request)
        if data['user'] in storage.config.users:
            storage.config.users.remove(data['user'])
            await storage.async_save_config()
        return self.json({"success": True})


class HeatgerAddZoneView(HomeAssistantView):
    """Add a zone (without actuator) by name"""

    url = "/api/heatger/zone/add"
    name = "api:heatger:zone:add"

    @RequestDataValidator(vol.Schema({vol.Required('zone'): cv.string}))
    @handle_errors
    async def post(self, request, data):
        storage = _storage(request)
        name = data['zone'].strip()
        if not name:
            raise HeatgerError('The zone needs a name')
        if any(zone.name == name for zone in storage.config.zones):
            raise HeatgerError(f'{name} already exists')
        zone = ZoneConfig.from_dict({'name': name})
        storage.config.zones.append(zone)
        await storage.async_save_config()
        schedule_reload(request.app["hass"])
        return self.json({"success": True, "id": zone.id})


class HeatgerRemoveZoneView(HomeAssistantView):
    """Remove a zone by name"""

    url = "/api/heatger/zone/remove"
    name = "api:heatger:zone:remove"

    @RequestDataValidator(vol.Schema({vol.Required('zone'): cv.string}))
    @handle_errors
    async def post(self, request, data):
        storage = _storage(request)
        zone = next((z for z in storage.config.zones if data['zone'] in (z.name, z.id)), None)
        if zone is None:
            raise HeatgerError(f'Zone {data["zone"]} not found')
        storage.config.zones.remove(zone)
        storage.persist.zones.pop(zone.id, None)
        await storage.async_save_config()
        await storage.async_save_persist()
        schedule_reload(request.app["hass"])
        return self.json({"success": True})


class HeatgerActivateFrostfreeView(HomeAssistantView):
    """Version 1 of the card: frost-free until a date = season stop until the date, then heating"""

    url = "/api/heatger/frostfree/activate"
    name = "api:heatger:frostfree:activate"

    @RequestDataValidator(vol.Schema({vol.Required('date'): cv.string}))
    @handle_errors
    async def post(self, request, data):
        until = str_to_datetime(data['date'])
        season = request.app["hass"].data[DOMAIN][DATA_SEASON]
        if until is None:
            raise HeatgerError(f'Invalid date: {data["date"]}')
        if until <= dt_util.now():
            # a date in the past stops the frost-free
            await season.async_set(Season.HEATING)
        else:
            await season.async_set(Season.STOP, until, Season.HEATING)
        return self.json({"success": True})


class HeatgerDeactivateFrostfreeView(HomeAssistantView):
    """Version 1 of the card: end of the frost-free = heating"""

    url = "/api/heatger/frostfree/deactivate"
    name = "api:heatger:frostfree:deactivate"

    @handle_errors
    async def post(self, request):
        await request.app["hass"].data[DOMAIN][DATA_SEASON].async_set(Season.HEATING)
        return self.json({"success": True})


async def async_register_api(hass):
    for view in (HeatgerAddProgView, HeatgerRemoveProgView, HeatgerRemoveAllProgView, HeatgerCopyProgView,
                 HeatgerAddUserView, HeatgerRemoveUserView, HeatgerAddZoneView, HeatgerRemoveZoneView,
                 HeatgerActivateFrostfreeView, HeatgerDeactivateFrostfreeView):
        hass.http.register_view(view)
