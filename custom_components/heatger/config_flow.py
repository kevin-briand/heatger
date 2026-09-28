"""Config flow for Heatger integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from .const import DOMAIN, IP, PORT
from .websocket.ws_client import WSClient

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(IP): str,
    vol.Required(PORT, default=5000): int,
})


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    if not 0 < data[PORT] <= 65535:
        raise InvalidPort()
    if len(data[IP].strip()) == 0:
        raise InvalidIp()

    ws_client = WSClient(hass, F"{data[IP].strip()}:{data[PORT]}")
    if not await ws_client.connect():
        raise CannotConnect
    await ws_client.disconnect()

    return {
        IP: F"{data[IP]}:{data[PORT]}",
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow"""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        # Only a single instance of the integration
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                user_input[IP] = user_input[IP].strip()
                return self.async_create_entry(title="Heatger", data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except (InvalidIp, InvalidPort):
                errors["base"] = "invalid_address"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found
        # with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidIp(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid ip."""


class InvalidPort(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid port."""
