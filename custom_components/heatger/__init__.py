"""Heatger integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api.ha_api import async_register_api
from .const import DOMAIN, IP
from .local_storage.config.config import Config
from .local_storage.persistence.persistence import Persistence
from .shared.logs.logs import Logs
from .websocket.ws_client import WSClient
from .websocket.ws_ha import async_register_ws
from .zone.zone_manager import ZoneManager
from .panel import (
    async_register_panel,
    async_unregister_panel,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heatger from a config entry."""
    await Persistence(hass).init_data()
    await Config(hass).get_config()
    hass.data.setdefault(DOMAIN, {})

    zone_manager = ZoneManager(hass)
    hass.data[DOMAIN]['zone_manager'] = zone_manager
    await zone_manager.run()

    try:
        ws = WSClient(hass, zone_manager.get_all_data, zone_manager.updated_state)
        hass.data[DOMAIN]['WS'] = ws
        await ws._auto_reconnect()
    except Exception as e:
        Logs.error('WS', e)

    await async_register_panel(hass)
    await async_register_api(hass)
    await async_register_ws(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload Heatger"""
    zone_manager: ZoneManager = hass.data.get(DOMAIN)['zone_manager']
    if zone_manager:
        await zone_manager.stop_loop()
        hass.data[DOMAIN].pop(entry.entry_id)

    await async_unregister_panel(hass)

    return True
