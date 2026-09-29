"""Heatger integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api.ha_api import async_register_api
from .const import (DATA_ENTRY, DATA_SEASON, DATA_SERVER_CONFIG, DATA_STORAGE, DATA_WS, DATA_ZONE_MANAGER, DOMAIN,
                    IP, PORT)
from .panel import RELOADING, async_register_panel, async_unregister_panel
from .season import SeasonManager
from .services import async_register_services, async_unregister_services
from .storage import HeatgerStorage
from .websocket.ws_client import WSClient
from .websocket.ws_ha import async_register_ws
from .zone.zone_manager import ZoneManager

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CLIMATE, Platform.SELECT, Platform.DATETIME,
             Platform.NUMBER]
# views and websocket commands can't be removed from HA, they are registered only once
HTTP_REGISTERED = f'{DOMAIN}_http_registered'


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heatger from a config entry."""
    hass.data.pop(RELOADING, None)
    storage = HeatgerStorage(hass)
    await storage.async_load()
    season = SeasonManager(hass, storage)
    zone_manager = ZoneManager(hass, storage, season)
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
        DATA_ENTRY: entry,
        DATA_STORAGE: storage,
        DATA_SEASON: season,
        DATA_ZONE_MANAGER: zone_manager,
        DATA_WS: ws,
        DATA_SERVER_CONFIG: server_config,
    }

    await season.async_init()
    await zone_manager.async_start()
    # send the current orders to the server
    await ws.send_data(await zone_manager.get_all_data())

    async_register_services(hass)
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
    zone_manager: ZoneManager | None = data.get(DATA_ZONE_MANAGER)
    if zone_manager:
        await zone_manager.async_stop()
    season: SeasonManager | None = data.get(DATA_SEASON)
    if season:
        await season.async_stop()
    ws: WSClient | None = data.get(DATA_WS)
    if ws:
        await ws.disconnect()

    async_unregister_services(hass)
    async_unregister_panel(hass)

    return True
