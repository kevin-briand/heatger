"""Coordinator class"""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.heatger.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SensorCoordinator(DataUpdateCoordinator):
    """Heatger coordinator: the data are pushed by the server (see WSClient.eval_message)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
        )
