"""object for config file"""
from dataclasses import dataclass

from custom_components.heatger.zone.dto.zone_dto import ZoneDto


@dataclass
class ConfigDto:
    """Config data object"""

    # pylint: disable=unused-argument
    def __init__(self, zones, users, ws_url=None, **kwargs):
        """
       Initialize ConfigDto with zones and users.

       :param zones: A list of zones, each being a dictionary or ZoneDto.
       :param users: A list of users.
       """
        self.zones = {}
        for i, (key, zone) in enumerate(zones.items()):
            self.zones[F'zone{i + 1}'] = zone if isinstance(zone, ZoneDto) else ZoneDto(**zone)
        self.users = users
        self.ws_url = ws_url if ws_url else None
