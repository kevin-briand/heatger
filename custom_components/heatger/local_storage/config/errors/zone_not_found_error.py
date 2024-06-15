"""ZoneNotFoundError Exception"""
from custom_components.heatger.local_storage.config.errors.config_error import ConfigError


class ZoneNotFoundError(ConfigError):
    """return a ZoneNotFound exception"""

    def __init__(self, zone_id: str):
        super().__init__(F"Zone {zone_id} not found !")
