"""Heatger panel registration"""
from homeassistant.components import frontend
from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL = '/api/panel_custom/heatger'
STATIC_REGISTERED = f'{DOMAIN}_static_registered'


async def async_register_panel(hass: HomeAssistant):
    """Register the Heatger panel in the sidebar"""
    if not hass.data.get(STATIC_REGISTERED):
        # a static path can't be registered twice (integration reload)
        path = hass.config.path(f'custom_components/{DOMAIN}/frontend/dist/heatger-panel.js')
        await hass.http.async_register_static_paths([
            StaticPathConfig(PANEL_URL, path, False)
        ])
        hass.data[STATIC_REGISTERED] = True

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name='heatger-panel',
        frontend_url_path=DOMAIN,
        module_url=PANEL_URL,
        sidebar_title='Heatger',
        sidebar_icon='mdi:radiator',
        require_admin=True,
        config={},
        config_panel_domain=DOMAIN,
    )


def async_unregister_panel(hass: HomeAssistant):
    """Remove the Heatger panel from the sidebar"""
    frontend.async_remove_panel(hass, DOMAIN)
