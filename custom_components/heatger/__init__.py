"""Heatger integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api.ha_api import async_register_api
from .const import DOMAIN, IP, PORT
from .local_storage.config.config import Config
from .local_storage.persistence.persistence import Persistence
from .websocket.ws_client import WSClient
from .websocket.ws_ha import async_register_ws
from .zone.zone_manager import ZoneManager
from .panel import (
    async_register_panel,
    async_unregister_panel,
)

PLATFORMS = [Platform.SENSOR]
# views and websocket commands can't be removed from HA, they are registered only once
HTTP_REGISTERED = f'{DOMAIN}_http_registered'


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heatger from a config entry."""
    await Persistence(hass).init_data()
    await Config(hass).get_config()

    zone_manager = ZoneManager(hass)
    ws = WSClient(hass, f'{entry.data[IP]}:{entry.data[PORT]}',
                  zone_manager.get_all_data, zone_manager.updated_state)

    if not await ws.connect():
        raise ConfigEntryNotReady(f'Unable to connect to the heatger server {ws.server_url}')
    server_config = await ws.get_config()
    if server_config is None:
        await ws.disconnect()
        raise ConfigEntryNotReady('The heatger server did not send its config')

    ws.set_as_main()
    hass.data[DOMAIN] = {
        'zone_manager': zone_manager,
        'WS': ws,
        'server_config': server_config,
    }

    await zone_manager.run()
    # send the current states to the server
    await ws.send_data(await zone_manager.get_all_data())

    if not hass.data.get(HTTP_REGISTERED):
        await async_register_api(hass)
        await async_register_ws(hass)
        hass.data[HTTP_REGISTERED] = True
    await async_register_panel(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Heatger"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    data = hass.data.pop(DOMAIN, {})
    zone_manager: ZoneManager | None = data.get('zone_manager')
    if zone_manager:
        await zone_manager.stop_loop()
        zone_manager.services_unregister()
    ws: WSClient | None = data.get('WS')
    if ws:
        await ws.disconnect()

    async_unregister_panel(hass)

    return True
