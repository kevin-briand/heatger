from functools import wraps
from http import HTTPStatus

from homeassistant.components.http.data_validator import RequestDataValidator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from custom_components.heatger import const as c
from custom_components.heatger.zone.zone_manager import ZoneManager
from custom_components.heatger.local_storage.config.config import Config
from custom_components.heatger.local_storage.errors.local_storage_error import LocalStorageError
from custom_components.heatger.shared.enum.state import State
from custom_components.heatger.shared.logs.logs import Logs
from custom_components.heatger.zone.dto.schedule_dto import ScheduleDto

DAYS = [0, 1, 2, 3, 4, 5, 6]
STATES = [state.value for state in State]


def handle_errors(func):
    """Return a clean json error instead of a 500 error"""
    @wraps(func)
    async def wrapper(view: HomeAssistantView, request, *args, **kwargs):
        if request.app["hass"].data.get(c.DOMAIN, {}).get('zone_manager') is None:
            return view.json_message('Heatger is not loaded', HTTPStatus.SERVICE_UNAVAILABLE)
        try:
            return await func(view, request, *args, **kwargs)
        except LocalStorageError as e:
            Logs.error('API', e)
            return view.json_message(str(e), HTTPStatus.BAD_REQUEST)
    return wrapper


class HeatgerAddProgView(HomeAssistantView):
    """Endpoint to adding new programs."""

    url = "/api/heatger/prog/add"
    name = "api:heatger:prog:add"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('zone_id'): cv.string,
                vol.Required('prog'): vol.All(
                    cv.ensure_list,
                    [
                        {
                            vol.Required('day'): vol.In(DAYS),
                            vol.Required('hour'): cv.string,
                            vol.Required('state'): vol.In(STATES)
                        }
                    ]
                )
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass = request.app["hass"]
        await Config(hass).add_schedules(data['zone_id'], ScheduleDto.from_array(data['prog']))
        manager: ZoneManager = hass.data[c.DOMAIN]['zone_manager']
        await manager.init_zones()
        return self.json({"success": True})


class HeatgerRemoveProgView(HomeAssistantView):
    """Endpoint to remove a program."""

    url = "/api/heatger/prog/remove"
    name = "api:heatger:prog:remove"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('zone_id'): cv.string,
                vol.Required('prog'): vol.All(
                    {
                        vol.Required('day'): vol.In(DAYS),
                        vol.Required('hour'): cv.string,
                        vol.Required('state'): vol.In(STATES)
                    }
                )
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass = request.app["hass"]
        await Config(hass).remove_schedule(data['zone_id'], ScheduleDto.from_dict(data['prog']))
        manager: ZoneManager = hass.data[c.DOMAIN]['zone_manager']
        await manager.init_zones()
        return self.json({"success": True})


class HeatgerRemoveAllProgView(HomeAssistantView):
    """Endpoint to remove all programs."""

    url = "/api/heatger/prog/removeall"
    name = "api:heatger:prog:removeall"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('zone_id'): cv.string
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass = request.app["hass"]
        await Config(hass).remove_all_schedule(data['zone_id'])
        manager: ZoneManager = hass.data[c.DOMAIN]['zone_manager']
        await manager.init_zones()
        return self.json({"success": True})


class HeatgerAddUserView(HomeAssistantView):
    """Endpoint to adding a new user."""

    url = "/api/heatger/user/add"
    name = "api:heatger:user:add"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('user'): cv.string
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass = request.app["hass"]
        await Config(hass).add_user(data['user'])
        return self.json({"success": True})


class HeatgerRemoveUserView(HomeAssistantView):
    """Endpoint to remove a user."""

    url = "/api/heatger/user/remove"
    name = "api:heatger:user:remove"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('user'): cv.string
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass = request.app["hass"]
        await Config(hass).remove_user(data['user'])
        return self.json({"success": True})


class HeatgerAddZoneView(HomeAssistantView):
    """Endpoint to adding a new zone."""

    url = "/api/heatger/zone/add"
    name = "api:heatger:zone:add"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('zone'): cv.string
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass = request.app["hass"]
        await Config(hass).add_zone(data['zone'])
        manager: ZoneManager = hass.data.get(c.DOMAIN)['zone_manager']
        await manager.init_zones()
        return self.json({"success": True})


class HeatgerRemoveZoneView(HomeAssistantView):
    """Endpoint to remove a zone."""

    url = "/api/heatger/zone/remove"
    name = "api:heatger:zone:remove"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('zone'): cv.string
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass: HomeAssistant = request.app["hass"]
        await Config(hass).remove_zone(data['zone'])
        manager: ZoneManager = hass.data[c.DOMAIN]['zone_manager']
        await manager.init_zones()
        return self.json({"success": True})


class HeatgerActivateFrostfreeView(HomeAssistantView):
    """Endpoint to activate frost-free."""

    url = "/api/heatger/frostfree/activate"
    name = "api:heatger:frostfree:activate"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required('date'): cv.string
            }
        )
    )
    @handle_errors
    async def post(self, request, data):
        hass: HomeAssistant = request.app["hass"]
        manager: ZoneManager = hass.data[c.DOMAIN]['zone_manager']
        await manager.toggle_frost_free(data['date'])
        return self.json({"success": True})


class HeatgerDeactivateFrostfreeView(HomeAssistantView):
    """Endpoint to deactivate frost-free."""

    url = "/api/heatger/frostfree/deactivate"
    name = "api:heatger:frostfree:deactivate"

    @handle_errors
    async def post(self, request):
        hass: HomeAssistant = request.app["hass"]
        manager: ZoneManager = hass.data[c.DOMAIN]['zone_manager']
        await manager.toggle_frost_free()
        return self.json({"success": True})


async def async_register_api(hass):
    hass.http.register_view(HeatgerAddProgView)
    hass.http.register_view(HeatgerRemoveProgView)
    hass.http.register_view(HeatgerRemoveAllProgView)
    hass.http.register_view(HeatgerAddUserView)
    hass.http.register_view(HeatgerRemoveUserView)
    hass.http.register_view(HeatgerAddZoneView)
    hass.http.register_view(HeatgerRemoveZoneView)
    hass.http.register_view(HeatgerActivateFrostfreeView)
    hass.http.register_view(HeatgerDeactivateFrostfreeView)
