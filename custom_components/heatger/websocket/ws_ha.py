"""WS endpoints register"""
import voluptuous as vol
from homeassistant.components.websocket_api import decorators, async_register_command
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers import config_validation as cv

from custom_components.heatger.const import DOMAIN
from custom_components.heatger.zone.zone_manager import ZoneManager
from custom_components.heatger.local_storage.config.config import Config


@callback
@decorators.websocket_command({
    vol.Required("type"): "heatger_get_prog",
    vol.Required("zone_id"): cv.string
})
@decorators.async_response
async def handle_get_prog(hass: HomeAssistant, connection, data):
    """Handle subscribe updates."""
    result = await Config(hass).get_zone(data['zone_id'])
    connection.send_result(data["id"], result)


@callback
@decorators.websocket_command({
    vol.Required("type"): "heatger_get_zones"
})
@decorators.async_response
async def handle_get_zones(hass: HomeAssistant, connection, data):
    """Handle subscribe updates."""
    result = Config(hass).data.zones
    connection.send_result(data["id"], result)


@callback
@decorators.websocket_command({
    vol.Required("type"): "heatger_get_zones_info"
})
@decorators.async_response
async def handle_get_zones_info(hass: HomeAssistant, connection, data):
    """Handle subscribe updates."""
    zm: ZoneManager = hass.data[DOMAIN]['zone_manager']
    result = await zm.get_zones_info()
    connection.send_result(data["id"], result)


@callback
@decorators.websocket_command({
    vol.Required("type"): "heatger_get_frostfree_info"
})
@decorators.async_response
async def handle_get_frostfree_info(hass: HomeAssistant, connection, data):
    """Handle subscribe updates."""
    zm: ZoneManager = hass.data[DOMAIN]['zone_manager']
    result = await zm.get_frostfree_info()
    connection.send_result(data["id"], result)


@callback
@decorators.websocket_command({
    vol.Required("type"): "heatger_get_available_persons",
})
@decorators.async_response
async def handle_get_available_persons(hass: HomeAssistant, connection, data):
    """Handle subscribe updates."""
    connection.send_result(data["id"], hass.states.async_all('person'))


@callback
@decorators.websocket_command({
    vol.Required("type"): "heatger_get_selected_persons",
})
@decorators.async_response
async def handle_get_selected_persons(hass: HomeAssistant, connection, data):
    """Handle subscribe updates."""
    result = (await Config(hass).get_config()).users
    connection.send_result(data["id"], result)


async def async_register_ws(hass):
    async_register_command(
        hass,
        handle_get_prog
    )

    async_register_command(
        hass,
        handle_get_zones
    )

    async_register_command(
        hass,
        handle_get_frostfree_info
    )

    async_register_command(
        hass,
        handle_get_zones_info
    )

    async_register_command(
        hass,
        handle_get_available_persons
    )

    async_register_command(
        hass,
        handle_get_selected_persons
    )
