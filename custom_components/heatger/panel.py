from homeassistant.components import frontend
from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig

from custom_components.heatger import DOMAIN


async def async_register_panel(hass):
    url = F'custom_components/{DOMAIN}/frontend/dist/heatger-panel.js'

    await hass.http.async_register_static_paths([
        StaticPathConfig('/api/panel_custom/heatger',url, False)
    ])

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name='heatger-panel',
        frontend_url_path=DOMAIN,
        module_url='/api/panel_custom/heatger',
        sidebar_title='Heatger',
        sidebar_icon='mdi:radiator',
        require_admin=True,
        config={},
        config_panel_domain=DOMAIN,
    )


def async_unregister_panel(hass):
    frontend.async_remove_panel(hass, DOMAIN)
